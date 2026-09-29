from urllib.parse import urlsplit
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from app.core.models import Company, PanelUser, Subscription
from app.uzytkownik.forms import EmployeeCreateForm


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DOMAIN_URL="https://panel.dapexa.com")
class EmployeeActivationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma")
        self.owner = PanelUser.objects.create_user(email="owner@example.test", password="test", company=self.company, role=PanelUser.Role.OWNER)
        self.employee = PanelUser.objects.create_user(email="employee@example.test", password=None, company=self.company, role=PanelUser.Role.MANAGER, is_active=False, is_active_employee=False)
        Subscription.objects.create(company=self.company, owner=self.owner, status=Subscription.STATUS_ACTIVE, package=Subscription.Package.STANDARD)
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")

    def url(self, action, employee=None):
        return reverse(action, kwargs={"pk": (employee or self.employee).pk})

    def assert_state(self, active, employee_active):
        self.employee.refresh_from_db()
        self.assertEqual((self.employee.is_active, self.employee.is_active_employee), (active, employee_active))

    def test_pending_account_cannot_be_enabled_by_direct_post(self):
        response = self.client.post(self.url("employee_status_toggle"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("Nie można aktywować pracownika", str(list(get_messages(response.wsgi_request))[0]))
        self.assert_state(False, False)

    def test_active_account_can_be_toggled_without_changing_activation(self):
        self.employee.is_active = True
        self.employee.set_password("test")
        self.employee.save()
        self.client.post(self.url("employee_status_toggle"))
        self.assert_state(True, True)
        self.client.post(self.url("employee_status_toggle"))
        self.assert_state(True, False)

    def test_inconsistent_legacy_employee_can_be_disabled(self):
        PanelUser.objects.filter(pk=self.employee.pk).update(is_active_employee=True)
        self.client.post(self.url("employee_status_toggle"))
        self.assert_state(False, False)

    def test_resend_and_first_password_complete_existing_flow(self):
        response = self.client.post(self.url("employee_resend_activation"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.employee.email])
        self.assertIn(self.employee.email, str(list(get_messages(response.wsgi_request))[0]))
        self.assert_state(False, False)
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("https://"))
        self.assertEqual(urlsplit(link).netloc, "panel.dapexa.com")
        client = Client()
        path = urlsplit(link).path
        self.assertEqual(client.get(path).status_code, 200)
        response = client.post(path, {"new_password1": "Strong!EmployeePassword123", "new_password2": "Strong!EmployeePassword123"})
        self.assertEqual(response.status_code, 302)
        self.assert_state(True, True)
        self.assertEqual(client.get(path).status_code, 302)

    def test_already_active_account_does_not_receive_activation(self):
        self.employee.is_active = True
        self.employee.set_password("test")
        self.employee.save()
        self.client.post(self.url("employee_resend_activation"))
        self.assertEqual(len(mail.outbox), 0)
        self.assert_state(True, False)

    def test_delivery_failures_preserve_account_and_do_not_expose_exception(self):
        for result in (OSError("secret-token"), 0):
            with self.subTest(result=type(result).__name__):
                kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
                with patch("django.core.mail.send_mail", **kwargs):
                    response = self.client.post(self.url("employee_resend_activation"))
                messages = " ".join(str(message) for message in get_messages(response.wsgi_request))
                self.assertIn("Nie udało się wysłać", messages)
                self.assertNotIn("secret-token", messages)
                self.assert_state(False, False)

    def test_other_company_client_owner_and_self_are_protected(self):
        other = Company.objects.create(name="Inna")
        outsider = PanelUser.objects.create_user(email="other@example.test", password="test", company=other, is_active=False, is_active_employee=False)
        customer = PanelUser.objects.create_user(email="customer@example.test", password="test", company=self.company, role=PanelUser.Role.CLIENT)
        for action in ("employee_status_toggle", "employee_resend_activation"):
            for employee, status in ((outsider, 404), (customer, 404), (self.owner, 403)):
                with self.subTest(action=action, employee=employee.pk):
                    self.assertEqual(self.client.post(self.url(action, employee)).status_code, status)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_csrf_and_login_are_required(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")
        for action in ("employee_status_toggle", "employee_resend_activation"):
            self.assertEqual(self.client.get(self.url(action)).status_code, 405)
            self.assertEqual(csrf_client.post(self.url(action)).status_code, 403)
            self.assertEqual(Client().post(self.url(action)).status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"])
    def test_manager_requires_existing_status_permission(self):
        manager = PanelUser.objects.create_user(email="manager@example.test", password="test", company=self.company, role=PanelUser.Role.MANAGER)
        self.client.force_login(manager, backend="django.contrib.auth.backends.ModelBackend")
        url = self.url("employee_resend_activation")
        self.assertEqual(self.client.post(url).status_code, 403)
        manager.user_permissions.add(Permission.objects.get(content_type__app_label="core", codename="access_employee_status_toggle"))
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_list_actions_match_account_state_in_desktop_and_mobile(self):
        response = self.client.get(reverse("employee_list"))
        self.assertContains(response, "Brak ustawionego hasła", count=2)
        self.assertContains(response, self.url("employee_resend_activation"), count=2)
        self.assertNotContains(response, self.url("employee_status_toggle"))
        self.employee.is_active = True
        self.employee.set_password("test")
        self.employee.save()
        response = self.client.get(reverse("employee_list"))
        self.assertNotContains(response, self.url("employee_resend_activation"))
        self.assertContains(response, self.url("employee_status_toggle"), count=2)

    def test_edit_form_cannot_bypass_pending_account_guard(self):
        form = EmployeeCreateForm(instance=self.employee, company=self.company, data={"email": self.employee.email, "role": self.employee.role, "is_active_employee": "on"})
        self.assertFalse(form.is_valid())
        self.assertIn("is_active_employee", form.errors)

    def test_company_is_required_even_for_owner(self):
        self.owner.company = None
        self.owner.save()
        for action in ("employee_status_toggle", "employee_resend_activation"):
            self.assertEqual(self.client.post(self.url(action)).status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_wrong_role_cannot_resend_even_with_permission(self):
        self.owner.role = PanelUser.Role.CLIENT
        self.owner.save()
        self.owner.user_permissions.add(Permission.objects.get(content_type__app_label="core", codename="access_employee_status_toggle"))
        self.assertEqual(self.client.post(self.url("employee_resend_activation")).status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_management_roles_keep_default_permission_to_resend(self):
        for role in (PanelUser.Role.MANAGER, PanelUser.Role.BIURO):
            with self.subTest(role=role):
                manager = PanelUser.objects.create_user(email=f"{role}@example.test", password="test", company=self.company, role=role)
                self.client.force_login(manager, backend="django.contrib.auth.backends.ModelBackend")
                self.assertEqual(self.client.post(self.url("employee_resend_activation")).status_code, 302)
        self.assertEqual(len(mail.outbox), 2)

    def test_activation_is_available_without_password_regardless_of_active_flag(self):
        self.employee.is_active = True
        self.employee.save()
        response = self.client.get(reverse("employee_list"))
        self.assertContains(response, self.url("employee_resend_activation"), count=2)
        self.assertContains(response, 'title="Wyślij link aktywacyjny"', count=2)
        self.assertNotContains(response, self.url("employee_status_toggle"))
        self.client.post(self.url("employee_status_toggle"))
        self.assert_state(True, False)
        self.client.post(self.url("employee_resend_activation"))
        self.assertEqual(len(mail.outbox), 1)
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("https://"))
        anonymous = Client()
        self.assertEqual(anonymous.get(urlsplit(link).path).status_code, 200)
        response = anonymous.post(urlsplit(link).path, {"new_password1": "Strong!EmployeePassword123", "new_password2": "Strong!EmployeePassword123"})
        self.assertEqual(response.status_code, 302)
        self.assert_state(True, True)
        self.assertTrue(self.employee.has_usable_password())

    def test_inactive_account_with_password_cannot_receive_first_password_link(self):
        self.employee.set_password("test")
        self.employee.save()
        self.client.post(self.url("employee_resend_activation"))
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.get(reverse("employee_list"))
        self.assertNotContains(response, self.url("employee_resend_activation"))
        self.client.post(self.url("employee_status_toggle"))
        self.assert_state(False, False)

    def test_edit_form_blocks_active_account_without_password(self):
        self.employee.is_active = True
        self.employee.save()
        form = EmployeeCreateForm(instance=self.employee, company=self.company, data={"email": self.employee.email, "role": self.employee.role, "is_active_employee": "on"})
        self.assertFalse(form.is_valid())
        self.assertIn("is_active_employee", form.errors)
