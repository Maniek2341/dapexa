from datetime import timedelta
from urllib.parse import urlsplit

from django.contrib.auth.hashers import make_password
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from app.core.models import Address, Company, PanelUser, Subscription
from app.uzytkownik.models import OwnershipTransfer


class TwoFactorLoginBackendTests(TestCase):
    def test_completing_legacy_two_factor_session_uses_model_backend(self):
        user = PanelUser.objects.create_user(
            email="twofactor@example.test",
            password="safe-test-password",
        )
        user.is_active = True
        user.is_superuser = True
        user.login_2fa_code_hash = make_password("123456")
        user.login_2fa_expires_at = timezone.now() + timedelta(minutes=5)
        user.save()

        session = self.client.session
        session["pending_2fa_user_id"] = user.pk
        session["pending_2fa_next"] = "/"
        session["pending_2fa_remember"] = True
        # Simulate an in-progress session created before backend tracking.
        session.save()

        response = self.client.post(reverse("login"), {"code": "123456"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session.get("_auth_user_backend"),
            "django.contrib.auth.backends.ModelBackend",
        )
        self.assertNotIn("pending_2fa_user_id", self.client.session)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DOMAIN_URL="https://panel.dapexa.com",
    PANEL_DOMAIN="panel.dapexa.com",
    DEFAULT_FROM_EMAIL="Dapexa <no-reply@dapexa.com>",
)
class ForgotPasswordEmailTests(TestCase):
    def setUp(self):
        self.user = PanelUser.objects.create_user(
            email="password-reset@example.test",
            password="safe-test-password",
        )

    def test_reset_request_sends_https_link_to_panel_domain(self):
        response = self.client.post(
            reverse("forgot"),
            {"email": self.user.email},
        )

        self.assertRedirects(response, reverse("login"))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.user.email])
        self.assertIn("https://panel.dapexa.com/uzytkownik/resetpassword/", message.body)
        html_message = str(message.alternatives[0][0])
        self.assertIn("https://panel.dapexa.com/uzytkownik/resetpassword/", html_message)
        self.assertNotIn("http://panel.dapexa.com", html_message)
        self.assertNotIn("Tradibis", html_message)

    def test_unknown_email_gets_same_confirmation_without_sending(self):
        response = self.client.post(
            reverse("forgot"),
            {"email": "unknown@example.test"},
        )

        self.assertRedirects(response, reverse("login"))
        self.assertEqual(len(mail.outbox), 0)


class RegistrationMailFailureTests(TestCase):
    def _post_signup(self):
        session = self.client.session
        session["registration_started_at"] = timezone.now().timestamp() - 10
        session.save()
        return self.client.post(
            reverse("register"),
            {
                "user-first_name": "Anna",
                "user-last_name": "Nowak",
                "user-email": "signup@example.test",
                "user-password1": "S3cure!Horse9Blue",
                "user-password2": "S3cure!Horse9Blue",
                "company-name": "Firma Testowa",
                "company-phone": "123456789",
                "company-street": "Ulica Testowa 1",
                "company-postcode": "00-001",
                "company-city": "Warszawa",
            },
        )

    @override_settings(EMAIL_HOST="smtp.example.test")
    @patch(
        "app.uzytkownik.views.user_register_view.send_activation_email",
        side_effect=OSError("SMTP unavailable"),
    )
    @patch(
        "app.core.geocoding.GeocodingService.get_coordinates",
        return_value=(None, None),
    )
    def test_failed_activation_email_rolls_back_registration(self, _geocode, _send_email):
        response = self._post_signup()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nie można wysłać wiadomości aktywacyjnej")
        self.assertFalse(PanelUser.objects.filter(email="signup@example.test").exists())
        self.assertFalse(Company.objects.exists())
        self.assertFalse(Address.objects.exists())
        self.assertFalse(Subscription.objects.exists())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @patch(
        "app.core.geocoding.GeocodingService.get_coordinates",
        return_value=(None, None),
    )
    def test_signup_succeeds_without_geocoding_when_mail_is_available(self, _geocode):
        response = self._post_signup()

        self.assertEqual(response.status_code, 302)
        user = PanelUser.objects.get(email="signup@example.test")
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.company)
        self.assertEqual(Subscription.objects.filter(owner=user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_HOST="")
    @patch("app.uzytkownik.views.user_register_view.send_activation_email")
    def test_missing_smtp_host_returns_message_without_creating_account(self, send_email):
        response = self._post_signup()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nie skonfigurowano wysyłki")
        send_email.assert_not_called()
        self.assertFalse(PanelUser.objects.filter(email="signup@example.test").exists())
        self.assertFalse(Company.objects.exists())
        self.assertFalse(Address.objects.exists())
        self.assertFalse(Subscription.objects.exists())


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DOMAIN_URL="https://panel.dapexa.com/",
)
class OwnershipTransferTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma testowa")
        self.owner = PanelUser.objects.create_user(
            email="owner@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.OWNER,
        )
        self.employee = PanelUser.objects.create_user(
            email="employee@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.MANAGER,
        )
        self.subscription = Subscription.objects.create(
            company=self.company,
            owner=self.owner,
            status=Subscription.STATUS_ACTIVE,
            package=Subscription.Package.STANDARD,
        )

    def _login(self, user):
        self.client.force_login(
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

    def test_transfer_requires_both_email_confirmations_and_is_single_use(self):
        self._login(self.owner)
        response = self.client.post(
            reverse("employee_ownership_transfer", kwargs={"pk": self.employee.pk})
        )

        self.assertRedirects(response, reverse("employee_list"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.owner.email])
        transfer = OwnershipTransfer.objects.get()
        self.assertEqual(transfer.status, OwnershipTransfer.Status.OWNER_PENDING)
        self.owner.refresh_from_db()
        self.employee.refresh_from_db()
        self.assertEqual(self.owner.role, PanelUser.Role.OWNER)
        self.assertEqual(self.employee.role, PanelUser.Role.MANAGER)

        owner_confirmation_url = next(
            line for line in mail.outbox[0].body.splitlines() if line.startswith("http")
        )
        self.assertTrue(owner_confirmation_url.startswith("https://panel.dapexa.com/"))
        owner_confirmation_path = owner_confirmation_url.removeprefix(
            "https://panel.dapexa.com"
        )
        anonymous_client = Client()

        self.assertEqual(anonymous_client.get(owner_confirmation_path).status_code, 200)
        self.assertEqual(anonymous_client.post(owner_confirmation_path).status_code, 200)

        transfer.refresh_from_db()
        self.owner.refresh_from_db()
        self.employee.refresh_from_db()
        self.assertEqual(transfer.status, OwnershipTransfer.Status.RECIPIENT_PENDING)
        self.assertEqual(self.owner.role, PanelUser.Role.OWNER)
        self.assertEqual(self.employee.role, PanelUser.Role.MANAGER)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, [self.employee.email])
        self.assertEqual(anonymous_client.post(owner_confirmation_path).status_code, 400)

        recipient_confirmation_url = next(
            line for line in mail.outbox[1].body.splitlines() if line.startswith("http")
        )
        self.assertTrue(recipient_confirmation_url.startswith("https://panel.dapexa.com/"))
        recipient_confirmation_path = recipient_confirmation_url.removeprefix(
            "https://panel.dapexa.com"
        )
        self.assertEqual(
            anonymous_client.get(recipient_confirmation_path).status_code,
            200,
        )
        self.assertEqual(
            anonymous_client.post(recipient_confirmation_path).status_code,
            302,
        )

        self.owner.refresh_from_db()
        self.employee.refresh_from_db()
        self.subscription.refresh_from_db()
        transfer.refresh_from_db()
        self.assertEqual(self.owner.role, PanelUser.Role.MANAGER)
        self.assertEqual(self.employee.role, PanelUser.Role.OWNER)
        self.assertEqual(self.subscription.owner, self.employee)
        self.assertEqual(transfer.status, OwnershipTransfer.Status.CONFIRMED)
        self.assertEqual(
            anonymous_client.post(recipient_confirmation_path).status_code,
            400,
        )

    def test_unsent_owner_email_preserves_existing_transfer(self):
        self._login(self.owner)
        url = reverse("employee_ownership_transfer", kwargs={"pk": self.employee.pk})
        self.client.post(url)
        transfer = OwnershipTransfer.objects.get()
        original_hash = transfer.token_hash

        with patch(
            "app.uzytkownik.views.employee_ownership_transfer_view.send_mail",
            return_value=0,
        ), self.assertLogs(
            "app.uzytkownik.views.employee_ownership_transfer_view", level="ERROR"
        ):
            response = self.client.post(url, follow=True)

        self.assertContains(response, "Nie udało się wysłać wiadomości potwierdzającej.")
        self.assertEqual(OwnershipTransfer.objects.count(), 1)
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, OwnershipTransfer.Status.OWNER_PENDING)
        self.assertEqual(transfer.token_hash, original_hash)

    def test_unsent_recipient_email_preserves_link_for_retry(self):
        self._login(self.owner)
        self.client.post(
            reverse("employee_ownership_transfer", kwargs={"pk": self.employee.pk})
        )
        transfer = OwnershipTransfer.objects.get()
        original_hash = transfer.token_hash
        original_expiry = transfer.expires_at
        path = urlsplit(next(
            line for line in mail.outbox[0].body.splitlines() if line.startswith("http")
        )).path
        anonymous_client = Client()
        with patch(
            "app.uzytkownik.views.employee_ownership_transfer_view.send_mail",
            return_value=0,
        ), self.assertLogs(
            "app.uzytkownik.views.employee_ownership_transfer_view", level="ERROR"
        ):
            response = anonymous_client.post(path)

        self.assertContains(
            response, "Nie udało się wysłać wiadomości przyszłemu właścicielowi.",
            status_code=503,
        )
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, OwnershipTransfer.Status.OWNER_PENDING)
        self.assertEqual(transfer.token_hash, original_hash)
        self.assertEqual(transfer.expires_at, original_expiry)
        self.owner.refresh_from_db()
        self.employee.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(self.owner.role, PanelUser.Role.OWNER)
        self.assertEqual(self.employee.role, PanelUser.Role.MANAGER)
        self.assertEqual(self.subscription.owner_id, self.owner.pk)

        self.assertEqual(anonymous_client.post(path).status_code, 200)
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, OwnershipTransfer.Status.RECIPIENT_PENDING)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, [self.employee.email])

    def test_non_owner_cannot_start_transfer(self):
        self._login(self.employee)
        response = self.client.post(
            reverse("employee_ownership_transfer", kwargs={"pk": self.owner.pk})
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(OwnershipTransfer.objects.exists())


class ProfileSubscriptionLimitsTests(TestCase):
    def setUp(self):
        address = Address(
            street="Testowa",
            street_no="1",
            postcode="00-001",
            city="Warszawa",
            country="Polska",
        )
        Address.objects.bulk_create([address])
        self.company = Company.objects.create(
            name="Firma profilu",
            nip="5260250274",
            main_address=address,
        )
        self.owner = PanelUser.objects.create_user(
            email="profile-owner@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.OWNER,
        )
        self.subscription = Subscription.objects.create(
            company=self.company,
            owner=self.owner,
            status=Subscription.STATUS_ACTIVE,
            package=Subscription.Package.START,
        )
        self.manager = PanelUser.objects.create_user(
            email="profile-manager@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.MANAGER,
        )
        self.employee = PanelUser.objects.create_user(
            email="profile-employee@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.EMPLOYEE,
        )

    def _profile_response(self, user):
        self.client.force_login(
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        return self.client.get(reverse("profile"))

    def test_owner_and_manager_see_package_limits(self):
        for user in [self.owner, self.manager]:
            with self.subTest(role=user.role):
                response = self._profile_response(user)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Pakiet i limity")
                self.assertContains(response, "5 GB")
                self.assertIsNotNone(response.context["subscription_summary"])

    def test_employee_does_not_see_package_limits(self):
        response = self._profile_response(self.employee)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Pakiet i limity")
        self.assertIsNone(response.context["subscription_summary"])

    @patch(
        "app.core.views.purchase_extra_users_view.sync_stripe_customer_billing_data",
        return_value="cus_test",
    )
    @patch(
        "app.core.views.purchase_extra_users_view.get_extra_user_price_id",
        return_value="price_extra_monthly",
    )
    @patch("app.core.views.purchase_extra_users_view.stripe.Subscription.modify")
    @patch("app.core.views.purchase_extra_users_view.stripe.Subscription.retrieve")
    def test_owner_can_purchase_extra_users(
        self,
        retrieve_subscription,
        modify_subscription,
        get_price,
        sync_customer,
    ):
        self.subscription.billing_period = Subscription.BILLING_MONTHLY
        self.subscription.stripe_subscription_id = "sub_test"
        self.subscription.save(
            update_fields=["billing_period", "stripe_subscription_id", "updated_at"]
        )
        retrieve_subscription.return_value = {
            "items": {
                "data": [
                    {
                        "id": "si_main",
                        "quantity": 1,
                        "price": {"id": "price_main", "lookup_key": None},
                    }
                ]
            }
        }
        modify_subscription.return_value = {
            "items": {
                "data": [
                    {
                        "id": "si_main",
                        "quantity": 1,
                        "price": {"id": "price_main", "lookup_key": None},
                    },
                    {
                        "id": "si_extra",
                        "quantity": 2,
                        "price": {
                            "id": "price_extra_monthly",
                            "lookup_key": "business_manager_extra_user_monthly_2500",
                        },
                    },
                ]
            },
            "pending_update": None,
        }

        self.client.force_login(
            self.owner,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        response = self.client.post(
            reverse("purchase_extra_users"),
            {"quantity": 2},
        )

        self.assertRedirects(response, reverse("profile"))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.extra_users, 2)
        self.assertEqual(self.subscription.max_users, 5)
        self.assertEqual(self.subscription.stripe_extra_user_item_id, "si_extra")
        get_price.assert_called_once_with(Subscription.BILLING_MONTHLY)
        sync_customer.assert_called_once()
        modify_subscription.assert_called_once()

    def test_manager_cannot_purchase_extra_users(self):
        self.client.force_login(
            self.manager,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        response = self.client.post(
            reverse("purchase_extra_users"),
            {"quantity": 1},
        )

        self.assertEqual(response.status_code, 403)
