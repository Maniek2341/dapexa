from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from app.core.models import Address, Company, PanelUser, Subscription
from app.uzytkownik.models import OwnershipTransfer


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
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
        owner_confirmation_path = owner_confirmation_url.removeprefix(
            "http://testserver"
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
        recipient_confirmation_path = recipient_confirmation_url.removeprefix(
            "http://testserver"
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
