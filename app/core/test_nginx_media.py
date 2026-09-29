"""Exercise real Nginx internal redirects against an isolated Django live server."""
import http.client
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from unittest import skipUnless
from urllib.parse import quote, urlsplit

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.handlers.wsgi import WSGIHandler
from django.test import LiveServerTestCase

from app.core.models import Company, PanelUser, Subscription
from app.dokument.models import Document


@skipUnless(shutil.which('nginx'), 'Nginx is required for the integration test')
class NginxPrivateMediaTests(LiveServerTestCase):
    # LiveServerTestCase normally serves media without reaching Django URLs.
    # Exercise the production WSGI handler, never that test-only file server.
    static_handler = staticmethod(lambda _handler: WSGIHandler())

    def test_authorized_download_internal_denial_and_byte_ranges(self):
        company = Company.objects.create(name='Isolated Nginx test')
        other = Company.objects.create(name='Other isolated tenant')
        user = PanelUser.objects.create_user('nginx@example.test', None, company=company, role='owner')
        Subscription.objects.create(company=company, owner=user, package=Subscription.Package.START, status=Subscription.STATUS_ACTIVE)
        contents = b'%PDF-1.4\nPrivate Nginx integration test\n'
        doc = Document.objects.create(company=company, name='Probe', file=SimpleUploadedFile('próba %.pdf', contents))
        denied = Document.objects.create(company=other, name='Other probe', file=SimpleUploadedFile('other.pdf', contents))
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        cookie = settings.SESSION_COOKIE_NAME + '=' + self.client.cookies[settings.SESSION_COOKIE_NAME].value
        with tempfile.TemporaryDirectory(prefix='dapexa-nginx-test-') as tmp:
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            server = Path(settings.BASE_DIR, 'deploy/nginx-dapexa.conf').read_text()
            server = server.replace('server unix:/run/dapexa/gunicorn.sock;', 'server ' + urlsplit(self.live_server_url).netloc + ';')
            first_server = server.index('server {')
            second_server = server.index('\nserver {', first_server + 1)
            server = server[:first_server] + server[second_server + 1:]
            server = server.replace('listen 443 ssl;', f'listen 127.0.0.1:{port};')
            server = server.replace('    ssl_certificate /etc/letsencrypt/live/%CERT_NAME%/fullchain.pem;\n', '')
            server = server.replace('    ssl_certificate_key /etc/letsencrypt/live/%CERT_NAME%/privkey.pem;\n', '')
            server = server.replace('%SERVER_NAMES%', 'localhost')
            server = server.replace('/var/www/dapexa/files/', str(Path(settings.MEDIA_ROOT)) + '/')
            server = server.replace('access_log /var/log/nginx/dapexa-access.log dapexa_safe;', 'access_log off;')
            server = server.replace('/var/log/nginx/dapexa-error.log', str(Path(tmp, 'error.log')))
            config = Path(tmp, 'nginx.conf')
            config.write_text(f'pid {tmp}/nginx.pid;\nerror_log stderr error;\nevents {{}}\nhttp {{\n'
                              f'client_body_temp_path {tmp}/client;\nproxy_temp_path {tmp}/proxy;\n'
                              f'fastcgi_temp_path {tmp}/fastcgi;\nuwsgi_temp_path {tmp}/uwsgi;\nscgi_temp_path {tmp}/scgi;\n'
                              'include /etc/nginx/mime.types;\n' + server + '\n}\n')
            command = ['nginx', '-p', tmp, '-c', str(config), '-e', 'stderr']
            check = subprocess.run([*command, '-t'], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            with Path(tmp, 'process.log').open('w') as log:
                process = subprocess.Popen([*command, '-g', 'daemon off;'], stdout=log, stderr=log)
                try:
                    for attempt in range(50):
                        try:
                            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                                break
                        except OSError:
                            time.sleep(0.1)
                    else:
                        self.fail('Isolated Nginx did not start')

                    def get(path, authenticated=False, method='GET', extra=None):
                        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
                        headers = {'Host': 'localhost'}
                        if authenticated:
                            headers['Cookie'] = cookie
                        headers.update(extra or {})
                        try:
                            conn.request(method, path, headers=headers)
                            response = conn.getresponse()
                            return response.status, dict(response.getheaders()), response.read()
                        finally:
                            conn.close()

                    self.assertEqual(get(doc.file.url)[0], 302)
                    self.assertEqual(get('/_protected_media/' + quote(doc.file.name, safe='/'))[0], 404)
                    status, headers, body = get(doc.file.url, True)
                    self.assertEqual(status, 200)
                    self.assertEqual(body, contents)
                    self.assertNotIn('X-Accel-Redirect', headers)
                    self.assertIn('private', headers['Cache-Control'])
                    self.assertEqual(get(denied.file.url, True)[0], 404)
                    self.assertEqual(get(doc.file.url, True, method='HEAD')[2], b'')
                    status, headers, body = get(doc.file.url, True, extra={'Range': 'bytes=0-3'})
                    self.assertEqual(status, 206)
                    self.assertEqual(body, contents[:4])
                    self.assertEqual(get('/static/assets/img/logo.png')[0], 200)
                finally:
                    process.terminate()
                    process.wait(timeout=10)
