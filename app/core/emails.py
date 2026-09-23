from django.core.mail import EmailMessage
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.conf import settings

def send_activation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    activation_url = request.build_absolute_uri(
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