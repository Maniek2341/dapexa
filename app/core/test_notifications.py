from unittest.mock import patch

from django.test import TestCase

from app.core.models import Company, CompanySettings, PanelUser
from app.core.notifications import notify_assigned_users, notify_company_email


class ActivityNotificationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Powiadomienia test")
        self.other_company = Company.objects.create(name="Inna firma")
        self.company_address = "alerts@example.test"
        CompanySettings.objects.update_or_create(
            company=self.company,
            defaults={
                "notification_email": self.company_address,
                "notification_modules": ["protokol"],
            },
        )
        self.assignee = PanelUser.objects.create_user(
            email="assigned@example.test", password="test-password",
            company=self.company, role=PanelUser.Role.EMPLOYEE,
        )
        self.foreign_user = PanelUser.objects.create_user(
            email="foreign@example.test", password="test-password",
            company=self.other_company, role=PanelUser.Role.EMPLOYEE,
        )

    @patch("app.core.notifications.send_mail")
    def test_company_mailbox_receives_only_enabled_module_notifications(self, send_mail):
        with self.captureOnCommitCallbacks(execute=True):
            notify_company_email(
                company=self.company,
                module="protokol",
                subject="Dodano protokół P-1",
                message="Nowy protokół",
            )
        send_mail.assert_called_once()
        self.assertEqual(send_mail.call_args.kwargs["recipient_list"], [self.company_address])

        send_mail.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            notify_company_email(
                company=self.company,
                module="serwis",
                subject="Nowy serwis",
                message="Nowy serwis",
            )
        send_mail.assert_not_called()

    @patch("app.core.notifications.send_mail")
    def test_assignee_gets_direct_notification_without_company_or_foreign_recipients(self, send_mail):
        with self.captureOnCommitCallbacks(execute=True):
            notify_assigned_users(
                company=self.company,
                users=[self.assignee, self.assignee, self.foreign_user],
                subject="Przypisano Ci pracę",
                message="Przypisano Cię do pracy.",
            )

        send_mail.assert_called_once()
        self.assertEqual(
            send_mail.call_args.kwargs["recipient_list"],
            [self.assignee.email],
        )
