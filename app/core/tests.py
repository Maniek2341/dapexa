import tempfile
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.core.cache import cache
from django.db import models
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.core.fields import TrackedFileField, TrackedImageField
from app.core.models import Address, Company, PanelUser, Subscription
from app.core.validators import is_valid_polish_nip
from app.core.subscription_limits import (
    BYTES_PER_GB,
    SubscriptionLimitExceeded,
    get_cached_company_storage_used_bytes,
)
from app.core.subscription_lifecycle import (
    add_months,
    purge_expired_subscriptions,
    send_cancellation_reminders,
)
from app.dokument.models import Document
from app.klient.models import Client
from app.protokol.models import Protocol
from app.core.views.views_stripe import (
    handle_subscription_updated,
    sync_stripe_customer_billing_data,
)
from app.core.views.views_stripe import STRIPE_PRICE_IDS


class TrackedFileSizeTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.media_directory.cleanup()

    def test_size_is_saved_when_file_is_added_replaced_and_cleared(self):
        user = PanelUser.objects.create_user(
            email="files@example.com",
            password="test-password",
            avatar=SimpleUploadedFile("avatar.txt", b"1234"),
        )
        self.assertEqual(user.avatar_size, 4)

        user.avatar = SimpleUploadedFile("new-avatar.txt", b"123456789")
        user.save(update_fields=["avatar"])
        user.refresh_from_db()
        self.assertEqual(user.avatar_size, 9)

        user.avatar = None
        user.save(update_fields=["avatar"])
        user.refresh_from_db()
        self.assertEqual(user.avatar_size, 0)

    def test_every_project_file_field_tracks_its_size(self):
        for model in apps.get_models():
            if not model._meta.app_config.name.startswith("app."):
                continue
            for field in model._meta.fields:
                if not isinstance(field, models.FileField):
                    continue
                self.assertIsInstance(
                    field,
                    (TrackedFileField, TrackedImageField),
                    f"{model._meta.label}.{field.name} nie śledzi rozmiaru",
                )
                size_field = model._meta.get_field(f"{field.name}_size")
                self.assertIsInstance(size_field, models.PositiveBigIntegerField)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SubscriptionLimitsTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name
        )
        self.settings_override.enable()
        self.company = Company.objects.create(name="Firma z limitami")
        self.owner = PanelUser.objects.create_user(
            email="limits@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.OWNER,
        )
        self.subscription = Subscription.objects.create(
            company=self.company,
            owner=self.owner,
            package=Subscription.Package.START,
            status=Subscription.STATUS_ACTIVE,
        )

    def tearDown(self):
        self.settings_override.disable()
        self.media_directory.cleanup()

    @patch("app.core.subscription_limits.get_company_storage_used_bytes")
    def test_profile_storage_usage_is_cached(self, calculate_storage):
        cache.clear()
        calculate_storage.return_value = 123

        self.assertEqual(get_cached_company_storage_used_bytes(self.company.pk), 123)
        self.assertEqual(get_cached_company_storage_used_bytes(self.company.pk), 123)
        calculate_storage.assert_called_once_with(self.company.pk)

    def test_user_client_and_protocol_limits_are_enforced(self):
        with patch.dict(
            Subscription.PACKAGE_LIMITS[Subscription.Package.START],
            {"max_users": 1, "max_clients": 1, "max_protocols": 1},
        ):
            with self.assertRaises(SubscriptionLimitExceeded):
                PanelUser.objects.create_user(
                    email="second@example.com",
                    password="test-password",
                    company=self.company,
                )

            client = Client.objects.create(company=self.company, name="Klient 1")
            with self.assertRaises(SubscriptionLimitExceeded):
                Client.objects.create(company=self.company, name="Klient 2")

            Protocol.objects.create(company=self.company, client=client)
            with self.assertRaises(SubscriptionLimitExceeded):
                Protocol.objects.create(company=self.company, client=client)

    def test_storage_limit_uses_sizes_from_all_file_models(self):
        eight_bytes_in_gb = 8 / BYTES_PER_GB
        with patch.dict(
            Subscription.PACKAGE_LIMITS[Subscription.Package.START],
            {"max_storage_gb": eight_bytes_in_gb},
        ):
            document = Document.objects.create(
                company=self.company,
                name="Pierwszy",
                file=SimpleUploadedFile("first.txt", b"1234"),
            )
            self.assertEqual(self.subscription.storage_used_bytes, 4)

            Document.objects.filter(company=self.company).update(file_size=0)
            self.assertEqual(self.subscription.storage_used_bytes, 4)
            self.assertEqual(
                Document.objects.get(company=self.company).file_size,
                4,
            )

            document.refresh_from_db()
            document.file = SimpleUploadedFile("replacement.txt", b"1234567")
            document.save(update_fields=["file"])
            self.assertEqual(self.subscription.storage_used_bytes, 7)

            with self.assertRaises(SubscriptionLimitExceeded):
                Document.objects.create(
                    company=self.company,
                    name="Drugi",
                    file=SimpleUploadedFile("second.txt", b"12"),
                )

    def test_unavailable_package_feature_redirects_to_plan_selection(self):
        self.client.force_login(
            self.owner,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        response = self.client.get(reverse("warranty_claim_list"))

        self.assertRedirects(response, reverse("select_plan"))

    def test_stripe_webhook_activates_paid_extra_users(self):
        self.subscription.stripe_subscription_id = "sub_extra_users"
        self.subscription.billing_period = Subscription.BILLING_MONTHLY
        self.subscription.save(
            update_fields=["stripe_subscription_id", "billing_period", "updated_at"]
        )

        handle_subscription_updated({
            "id": "sub_extra_users",
            "status": Subscription.STATUS_ACTIVE,
            "cancel_at_period_end": False,
            "current_period_start": None,
            "current_period_end": None,
            "items": {
                "data": [
                    {
                        "id": "si_main",
                        "quantity": 1,
                        "price": {"id": "price_main", "lookup_key": None},
                    },
                    {
                        "id": "si_extra_users",
                        "quantity": 4,
                        "price": {
                            "id": "price_extra",
                            "lookup_key": "business_manager_extra_user_monthly_2500",
                        },
                    },
                ]
            },
        })

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.extra_users, 4)
        self.assertEqual(self.subscription.max_users, 7)
        self.assertEqual(
            self.subscription.stripe_extra_user_item_id,
            "si_extra_users",
        )


class PackageChangeTests(TestCase):
    def setUp(self):
        address = Address(
            street="Testowa",
            street_no="2",
            postcode="00-002",
            city="Warszawa",
            country="Polska",
        )
        Address.objects.bulk_create([address])
        self.company = Company.objects.create(
            name="Firma zmiana pakietu",
            nip="5260250274",
            main_address=address,
        )
        self.owner = PanelUser.objects.create_user(
            email="package-owner@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.OWNER,
        )
        self.subscription = Subscription.objects.create(
            company=self.company,
            owner=self.owner,
            package=Subscription.Package.START,
            billing_period=Subscription.BILLING_MONTHLY,
            status=Subscription.STATUS_ACTIVE,
            stripe_subscription_id="sub_package_change",
            stripe_extra_user_item_id="si_extra",
            extra_users=2,
        )
        self.client.force_login(
            self.owner,
            backend="django.contrib.auth.backends.ModelBackend",
        )

    @patch(
        "app.core.views.change_package_view.sync_stripe_customer_billing_data",
        return_value="cus_package",
    )
    @patch(
        "app.core.views.change_package_view.get_extra_user_price_id",
        return_value="price_extra_yearly",
    )
    @patch("app.core.views.change_package_view.stripe.Subscription.modify")
    @patch("app.core.views.change_package_view.stripe.Subscription.retrieve")
    def test_changes_existing_plan_and_preserves_extra_users(
        self,
        retrieve_subscription,
        modify_subscription,
        get_extra_price,
        sync_customer,
    ):
        retrieve_subscription.return_value = {
            "items": {"data": [
                {
                    "id": "si_main",
                    "quantity": 1,
                    "price": {
                        "id": STRIPE_PRICE_IDS["start"]["monthly"],
                        "lookup_key": None,
                    },
                },
                {
                    "id": "si_extra",
                    "quantity": 2,
                    "price": {
                        "id": "price_extra_monthly",
                        "lookup_key": "business_manager_extra_user_monthly_2500",
                    },
                },
            ]},
        }
        modify_subscription.return_value = {
            "status": Subscription.STATUS_ACTIVE,
            "pending_update": None,
            "items": {"data": [
                {
                    "id": "si_main",
                    "quantity": 1,
                    "price": {
                        "id": STRIPE_PRICE_IDS["standard"]["yearly"],
                        "lookup_key": None,
                    },
                },
                {
                    "id": "si_extra",
                    "quantity": 2,
                    "price": {
                        "id": "price_extra_yearly",
                        "lookup_key": "business_manager_extra_user_yearly_25000",
                    },
                },
            ]},
        }

        response = self.client.post(
            reverse("change_package"),
            {"package": "standard", "billing_period": "yearly"},
        )

        self.assertRedirects(response, reverse("profile"))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.package, Subscription.Package.STANDARD)
        self.assertEqual(
            self.subscription.billing_period,
            Subscription.BILLING_YEARLY,
        )
        self.assertEqual(self.subscription.extra_users, 2)
        get_extra_price.assert_called_once_with(Subscription.BILLING_YEARLY)
        sync_customer.assert_called_once()
        sent_items = modify_subscription.call_args.kwargs["items"]
        self.assertEqual(sent_items[0]["id"], "si_main")
        self.assertEqual(sent_items[1]["quantity"], 2)

    @patch(
        "app.core.views.change_package_view.sync_stripe_customer_billing_data",
        return_value="cus_package",
    )
    @patch("app.core.views.change_package_view.stripe.checkout.Session.create")
    def test_trial_starts_paid_plan_through_checkout(
        self, create_session, sync_customer
    ):
        self.subscription.package = Subscription.Package.TRIAL
        self.subscription.billing_period = None
        self.subscription.status = Subscription.STATUS_TRIALING
        self.subscription.stripe_subscription_id = None
        self.subscription.stripe_extra_user_item_id = ""
        self.subscription.extra_users = 0
        self.subscription.save()
        create_session.return_value = SimpleNamespace(
            url="https://checkout.stripe.com/test-session"
        )

        response = self.client.post(
            reverse("change_package"),
            {"package": "start", "billing_period": "monthly"},
        )

        self.assertRedirects(
            response,
            "https://checkout.stripe.com/test-session",
            fetch_redirect_response=False,
        )
        metadata = create_session.call_args.kwargs["metadata"]
        self.assertEqual(metadata["local_subscription_id"], str(self.subscription.pk))
        sync_customer.assert_called_once()

    def test_manager_cannot_change_package(self):
        manager = PanelUser.objects.create_user(
            email="package-manager@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.MANAGER,
        )
        self.client.force_login(
            manager,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        response = self.client.post(
            reverse("change_package"),
            {"package": "standard", "billing_period": "monthly"},
        )

        self.assertEqual(response.status_code, 403)

    def test_current_package_is_blocked_server_side(self):
        with patch("app.core.views.change_package_view.stripe.Subscription.retrieve") as retrieve:
            response = self.client.post(
                reverse("change_package"),
                {"package": "start", "billing_period": "yearly"},
            )

        self.assertRedirects(response, reverse("select_plan"))
        retrieve.assert_not_called()

    @patch("app.core.views.change_package_view.stripe.checkout.Session.create")
    def test_current_package_without_stripe_id_is_also_blocked(self, create_session):
        self.subscription.stripe_subscription_id = None
        self.subscription.status = Subscription.STATUS_CANCELED
        self.subscription.save(
            update_fields=["stripe_subscription_id", "status", "updated_at"]
        )

        response = self.client.post(
            reverse("change_package"),
            {"package": "start", "billing_period": "yearly"},
        )

        self.assertRedirects(response, reverse("select_plan"))
        create_session.assert_not_called()

    def test_invalid_nip_blocks_payment(self):
        self.company.nip = "1234567890"
        self.company.save(update_fields=["nip", "updated_at"])
        response = self.client.post(
            reverse("change_package"),
            {"package": "standard", "billing_period": "monthly"},
        )

        self.assertRedirects(response, reverse("company_settings"))

    def test_polish_nip_checksum_validation(self):
        self.assertTrue(is_valid_polish_nip("526-025-02-74"))
        self.assertFalse(is_valid_polish_nip("1234567890"))
        self.assertFalse(is_valid_polish_nip("0000000000"))

    @patch("app.core.views.views_stripe.stripe.Customer.create_tax_id")
    @patch("app.core.views.views_stripe.stripe.Customer.delete_tax_id")
    @patch("app.core.views.views_stripe.stripe.Customer.list_tax_ids")
    @patch("app.core.views.views_stripe.stripe.Customer.modify")
    def test_company_billing_data_and_nip_are_synced_to_stripe(
        self,
        modify_customer,
        list_tax_ids,
        delete_tax_id,
        create_tax_id,
    ):
        self.subscription.stripe_customer_id = "cus_company"
        modify_customer.return_value = SimpleNamespace(id="cus_company")
        list_tax_ids.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    id="txi_old",
                    type="pl_nip",
                    value="1111111111",
                )
            ]
        )

        sync_stripe_customer_billing_data(
            self.subscription,
            self.company,
            self.owner.email,
        )

        customer_data = modify_customer.call_args.kwargs
        self.assertEqual(customer_data["name"], self.company.name)
        self.assertEqual(customer_data["address"]["country"], "PL")
        delete_tax_id.assert_called_once_with("cus_company", "txi_old")
        create_tax_id.assert_called_once_with(
            "cus_company",
            type="pl_nip",
            value="5260250274",
        )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SubscriptionCancellationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma anulująca")
        self.owner = PanelUser.objects.create_user(
            email="cancel-owner@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.OWNER,
        )
        self.period_end = timezone.now() + timedelta(days=30)
        self.subscription = Subscription.objects.create(
            company=self.company,
            owner=self.owner,
            package=Subscription.Package.START,
            billing_period=Subscription.BILLING_MONTHLY,
            status=Subscription.STATUS_ACTIVE,
            stripe_subscription_id="sub_cancel",
            current_period_end=self.period_end,
        )
        self.client.force_login(
            self.owner,
            backend="django.contrib.auth.backends.ModelBackend",
        )

    @patch("app.core.views.cancel_subscription_view.stripe.Subscription.modify")
    def test_owner_cancels_at_period_end_without_immediate_account_block(self, modify):
        modify.return_value = {
            "status": Subscription.STATUS_ACTIVE,
            "cancel_at_period_end": True,
            "current_period_end": int(self.period_end.timestamp()),
        }

        response = self.client.post(reverse("cancel_subscription"))

        self.assertRedirects(response, reverse("profile"))
        modify.assert_called_once_with("sub_cancel", cancel_at_period_end=True)
        self.subscription.refresh_from_db()
        self.assertTrue(self.subscription.cancel_at_period_end)
        self.assertEqual(
            self.subscription.data_retention_until,
            add_months(self.subscription.current_period_end, 6),
        )
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_account_is_blocked_only_after_canceled_period_ends(self):
        self.subscription.cancel_at_period_end = True
        self.subscription.current_period_end = timezone.now() - timedelta(seconds=1)
        self.subscription.data_retention_until = add_months(
            self.subscription.current_period_end, 6
        )
        self.subscription.save()

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("select_plan"))

    def test_reminder_is_sent_once_during_last_three_days(self):
        now = timezone.now()
        self.subscription.cancel_at_period_end = True
        self.subscription.current_period_end = now + timedelta(days=3)
        self.subscription.data_retention_until = add_months(
            self.subscription.current_period_end, 6
        )
        self.subscription.save()

        self.assertEqual(send_cancellation_reminders(now=now), 1)
        self.assertEqual(send_cancellation_reminders(now=now), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.company.name, mail.outbox[0].body)

    def test_data_is_not_purged_before_retention_deadline(self):
        self.subscription.cancel_at_period_end = True
        self.subscription.data_retention_until = timezone.now() + timedelta(days=1)
        self.subscription.save()

        self.assertEqual(purge_expired_subscriptions(), 0)
        self.assertTrue(Company.objects.filter(pk=self.company.pk).exists())

    def test_company_data_is_purged_after_six_month_retention(self):
        self.subscription.cancel_at_period_end = True
        self.subscription.data_retention_until = timezone.now() - timedelta(seconds=1)
        self.subscription.save()

        self.assertEqual(purge_expired_subscriptions(), 1)
        self.assertFalse(Company.objects.filter(pk=self.company.pk).exists())
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.is_active)
        self.assertIsNone(self.owner.company_id)
