from django.conf import settings
from django.core.mail import send_mail

from app.core.models import CompanySettings, PanelUser
from app.core.notification_preferences import NOTIFICATION_MODULE_CHOICES


VALID_NOTIFICATION_MODULES = {code for code, _label in NOTIFICATION_MODULE_CHOICES}


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
