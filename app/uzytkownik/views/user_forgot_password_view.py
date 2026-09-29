import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views import View

from app.uzytkownik.forms import ForgotForm
from app.core.emails import build_email_url
from app.core.models import PanelUser

logger = logging.getLogger(__name__)


def _message(title, body):
    return json.dumps({"title": title, "body": body})


class UserForgotPasswordView(View):
    reset_token = PasswordResetTokenGenerator()
    title = 'Forgot password'

    def get(self, request):
        context = {
            'title': self.title,
            'forgot_form': ForgotForm()
        }
        return render(request, 'app/uzytkownik/forgotpassword.html', context)

    def post(self, request):
        forgot_form = ForgotForm(request.POST)
        if not forgot_form.is_valid():
            return render(request, "app/uzytkownik/forgotpassword.html", {
                "title": self.title,
                "forgot_form": forgot_form,
            })

        email = forgot_form.cleaned_data["email"].strip()
        user = PanelUser.objects.filter(email__iexact=email, is_active=True).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = self.reset_token.make_token(user)
            reset_path = reverse("resetpassword", kwargs={"uidb64": uid, "token": token})
            domain_url = settings.DOMAIN_URL.rstrip("/")
            reset_url = build_email_url(reset_path)
            mail_content = {
                "user": user,
                "email": user.email,
                "domain": settings.PANEL_DOMAIN,
                "domain_url": domain_url,
                "reset_url": reset_url,
                "uid": uid,
                "token": token,
            }
            html_message = render_to_string(
                "app/mail/forgot_password_confirmation.html",
                mail_content,
                request=request,
            )
            text_message = (
                "Aby ustawić nowe hasło do konta Dapexa, otwórz ten link:\n"
                f"{reset_url}\n\nJeśli nie prosisz o zmianę hasła, zignoruj tę wiadomość."
            )

            try:
                sent_count = send_mail(
                    subject="Link do zmiany hasła — Dapexa",
                    message=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                    html_message=html_message,
                )
                if sent_count != 1:
                    raise RuntimeError("Email backend did not accept the reset message")
            except Exception as exc:
                logger.error("Password reset email delivery failed (%s)", type(exc).__name__)
                messages.error(
                    request,
                    _message("Nie udało się wysłać wiadomości", "Spróbuj ponownie za chwilę."),
                )
                return redirect("login")

        # Keep the response identical for known, inactive, and unknown addresses.
        messages.info(
            request,
            _message(
                "Sprawdź swoją pocztę",
                "Jeśli aktywne konto jest przypisane do tego adresu, wyślemy link do zmiany hasła.",
            ),
        )
        return redirect("login")
