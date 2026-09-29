from urllib.parse import urlsplit

from django.contrib.sites.models import Site
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve

from app.core.emails import send_activation_email
from app.core.models import Company, PanelUser
from app.uzytkownik.views.employee_create_view import EmployeeCreateView


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DOMAIN_URL="https://panel.dapexa.com/",
    SITE_ID=1,
)
class ActivationEmailDomainTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test")
        self.user = PanelUser.objects.create_user(
            email="employee@example.test", password="test-password",
            company=self.company,
        )
        Site.objects.update_or_create(pk=1, defaults={"domain": "example.com"})
        Site.objects.clear_cache()
        self.addCleanup(Site.objects.clear_cache)
        self.request = RequestFactory().get("/", HTTP_HOST="localhost")
        self.request.user = self.user

    def assert_email_link(self, view_name):
        self.assertEqual(len(mail.outbox), 1)
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
        parsed = urlsplit(link)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "panel.dapexa.com")
        self.assertFalse(parsed.path.startswith("//"))
        self.assertEqual(resolve(parsed.path).url_name, view_name)

    def test_registration_ignores_request_domain_and_scheme(self):
        send_activation_email(self.request, self.user)
        self.assert_email_link("user_activate")

    def test_employee_activation_ignores_site_domain_and_request_scheme(self):
        view = EmployeeCreateView()
        view.setup(self.request)
        view._send_activation_email(self.user)
        self.assert_email_link("employee_set_password")
