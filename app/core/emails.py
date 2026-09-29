from django.core.mail import EmailMessage
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.conf import settings

def build_email_url(path):
    """Build email links using the configured public panel URL."""
    return f"{settings.DOMAIN_URL.rstrip('/')}/{path.lstrip('/')}"


def send_activation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    activation_url = build_email_url(
        reverse("user_activate", kwargs={
            "uidb64": uid,
            "token": token,
        })
    )

    subject = "Aktywuj swoje konto"
    body = f"""
Cześć {user.first_name or user.email},

Dziękujemy za rejestrację konta.

Aby aktywować konto, kliknij w link poniżej:
{activation_url}

Jeżeli to nie Ty zakładałeś konto – zignoruj tę wiadomość.
"""

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.send(fail_silently=False)


def send_employee_activation_email(employee):
    """Send the existing first-password activation without changing account state."""
    from django.contrib.auth.tokens import PasswordResetTokenGenerator
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    uid = urlsafe_base64_encode(force_bytes(employee.pk))
    token = PasswordResetTokenGenerator().make_token(employee)
    activation_link = build_email_url(
        reverse("employee_set_password", kwargs={"uidb64": uid, "token": token})
    )
    message = render_to_string(
        "app/pracownik/activation_email.txt",
        {"employee": employee, "activation_link": activation_link, "company": employee.company},
    )
    sent = send_mail(
        subject="Aktywacja konta – ustaw hasło",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[employee.email],
        fail_silently=False,
    )
    if sent != 1:
        raise RuntimeError("Email backend did not accept the activation message")
