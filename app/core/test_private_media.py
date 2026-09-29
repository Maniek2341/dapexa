from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

from django.apps import apps
from django.conf import settings
from django.db import models
from django.test import TestCase, override_settings

from app.core.models import Company, PanelUser, Subscription
from app.core.private_media import FILE_POLICIES
from app.dokument.models import Document
from app.uzytkownik.models import EmployeeContract


class PrivateMediaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name='Media test')
        cls.other = Company.objects.create(name='Other tenant')
        cls.owner = PanelUser.objects.create_user(password=None, email='owner@media.test', company=cls.company, role='owner')
        cls.employee = PanelUser.objects.create_user(password=None, email='worker@media.test', company=cls.company, role='employee')
        cls.colleague = PanelUser.objects.create_user(password=None, email='other@media.test', company=cls.company, role='employee')
        cls.subscription = Subscription.objects.create(company=cls.company, owner=cls.owner, package=Subscription.Package.START, status=Subscription.STATUS_ACTIVE)

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.directory.name, DEBUG=False)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")

    def document(self, name='companies/test/document.pdf', company=None):
        p = Path(self.directory.name) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'%PDF-1.4\nTest')
        return Document.objects.create(company=company or self.company, name='Test', file=name, file_size=p.stat().st_size)

    def test_every_file_field_has_an_explicit_policy(self):
        actual = {(m._meta.label, f.name) for m in apps.get_models() if m._meta.app_config.name.startswith('app.') for f in m._meta.fields if isinstance(f, models.FileField)}
        self.assertEqual(actual, {(label, field) for label, field, *_ in FILE_POLICIES})

    def test_authorized_response_offloads_without_returning_bytes(self):
        doc = self.document('companies/test/zażółć %.pdf')
        response = self.client.get(doc.file.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        self.assertEqual(response['X-Accel-Redirect'], settings.PRIVATE_MEDIA_INTERNAL_URL + quote(doc.file.name, safe='/'))
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_anonymous_is_redirected_without_accel_header(self):
        doc = self.document()
        self.client.logout()
        response = self.client.get(doc.file.url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('X-Accel-Redirect', response)

    def test_other_tenant_and_unregistered_file_are_denied(self):
        doc = self.document(company=self.other)
        response = self.client.get(doc.file.url)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('X-Accel-Redirect', response)
        Path(self.directory.name, 'orphan.pdf').write_bytes(b'not a registered file')
        self.assertEqual(self.client.get('/files/orphan.pdf').status_code, 404)

    def test_employee_without_document_permission_is_denied(self):
        doc = self.document()
        self.client.force_login(self.employee, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(self.client.get(doc.file.url).status_code, 404)

    def test_employee_only_reads_own_contract(self):
        for employee in [self.employee, self.colleague]:
            name = f'contracts/{employee.pk}.pdf'
            p = Path(self.directory.name, name)
            p.parent.mkdir(exist_ok=True)
            p.write_bytes(b'%PDF-1.4\nTest')
            EmployeeContract.objects.create(company=self.company, employee=employee, date_from='2026-01-01', contract_image=name, contract_image_size=p.stat().st_size)
        self.client.force_login(self.employee, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(self.client.get(f'/files/contracts/{self.employee.pk}.pdf').status_code, 200)
        self.assertEqual(self.client.get(f'/files/contracts/{self.colleague.pk}.pdf').status_code, 404)

    def test_traversal_symlinks_and_missing_files_are_denied(self):
        doc = self.document()
        for path in ['/files/../.env', '/files/%2e%2e/.env', '/files/a%5c..%5c.env']:
            self.assertEqual(self.client.get(path).status_code, 404)
        p = Path(doc.file.path)
        p.unlink()
        p.symlink_to(Path(settings.BASE_DIR, '.env'))
        self.assertEqual(self.client.get(doc.file.url).status_code, 404)
        p.unlink()
        self.assertEqual(self.client.get(doc.file.url).status_code, 404)

    def test_active_html_is_downloaded_as_binary(self):
        doc = self.document('test.html')
        response = self.client.get(doc.file.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        self.assertEqual(response['Content-Security-Policy'], 'sandbox')

    def test_inactive_employee_cannot_use_existing_session(self):
        doc = self.document()
        PanelUser.objects.filter(pk=self.owner.pk).update(is_active_employee=False)
        response = self.client.get(doc.file.url)
        self.assertNotIn('X-Accel-Redirect', response)
        self.assertNotEqual(response.status_code, 200)

    def test_post_is_not_allowed(self):
        doc = self.document()
        self.assertEqual(self.client.post(doc.file.url).status_code, 405)

    def test_package_and_expired_subscription_block_download(self):
        doc = self.document()
        from unittest.mock import patch
        with patch.object(Subscription, 'has_feature', return_value=False):
            self.assertEqual(self.client.get(doc.file.url).status_code, 404)
        self.subscription.status = Subscription.STATUS_UNPAID
        self.subscription.save(update_fields=['status'])
        self.assertEqual(self.client.get(doc.file.url).status_code, 302)

    @override_settings(DEBUG=True)
    def test_development_uses_the_same_authorization(self):
        doc = self.document()
        response = self.client.get(doc.file.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))
        response.close()
        doc.company = self.other
        doc.save(update_fields=['company'])
        self.assertEqual(self.client.get(doc.file.url).status_code, 404)
