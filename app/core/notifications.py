from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
import logging

from app.core.models import CompanySettings, PanelUser
from app.core.notification_preferences import NOTIFICATION_MODULE_CHOICES


VALID_NOTIFICATION_MODULES = {code for code, _label in NOTIFICATION_MODULE_CHOICES}
logger = logging.getLogger(__name__)


def _queue_notification_email(recipients, subject, message):
    recipients = sorted({email.strip().lower() for email in recipients if email and email.strip()})
    if not recipients:
        return

    def deliver():
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
        except Exception:
            # Powiadomienie nie może wycofać zapisanego obiektu ani przerwać pracy.
            logger.exception("Nie udało się wysłać powiadomienia e-mail: %s", subject)

    transaction.on_commit(deliver)


def notify_company_email(*, company, module, subject, message):
    """Notify the configured company mailbox when this module is enabled."""
    if module not in VALID_NOTIFICATION_MODULES:
        raise ValueError(f"Nieznany moduł powiadomień: {module}")

    company_settings = CompanySettings.objects.filter(company=company).first()
    if not company_settings or module not in (company_settings.notification_modules or []):
        return
    _queue_notification_email([company_settings.notification_email], subject, message)


def notify_assigned_users(*, company, users, subject, message):
    """Notify assigned people directly, independent of their optional preferences."""
    recipients = []
    for user in users:
        if (
            user.company_id == company.pk
            and user.is_active
            and getattr(user, "is_active_employee", True)
            and user.email
        ):
            recipients.append(user.email)
    _queue_notification_email(recipients, subject, message)


def get_module_notification_recipients(company, module):
    """Return unique company and user e-mail recipients subscribed to a module."""
    if module not in VALID_NOTIFICATION_MODULES:
        raise ValueError(f"Nieznany moduł powiadomień: {module}")

    recipients = set()
    company_settings = CompanySettings.objects.filter(company=company).first()
    if (
        company_settings
        and company_settings.notification_email
        and module in (company_settings.notification_modules or [])
    ):
        recipients.add(company_settings.notification_email.strip().lower())

    users = PanelUser.objects.filter(
        company=company,
        is_active=True,
        is_active_employee=True,
    ).exclude(email="")
    for user in users.only("email", "email_notification_modules"):
        if module in (user.email_notification_modules or []):
            recipients.add(user.email.strip().lower())

    return sorted(recipients)


def send_module_notification(*, company, module, subject, message, fail_silently=True):
    recipients = get_module_notification_recipients(company, module)
    if not recipients:
        return 0
    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=fail_silently,
    )
