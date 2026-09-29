# app/uzytkownik/views/user_register_view.py
from datetime import timedelta
import json
import logging
import os
import traceback
from smtplib import SMTPException

from django.contrib import messages
from django.conf import settings
from django.db import transaction

from django.views import View
from django.shortcuts import render, redirect
from django.utils import timezone
from app.core.emails import send_activation_email

from app.core.forms import (
    UserRegistrationForm,
    CompanyForm,
)
from app.core.models import Address, Subscription

REGISTRATION_STARTED_SESSION_KEY = "registration_started_at"
REGISTRATION_MIN_SECONDS = 3
logger = logging.getLogger(__name__)


def _log_sanitized_registration_exception(exc):
    frames = traceback.extract_tb(exc.__traceback__)
    locations = " > ".join(
        f"{os.path.basename(frame.filename)}:{frame.lineno}:{frame.name}"
        for frame in frames[-5:]
    )
    logger.error(
        "Unexpected registration failure (%s); traceback locations: %s",
        type(exc).__name__,
        locations,
    )

def create_trial_subscription(company, owner):
    return Subscription.objects.create(
        company=company,
        owner=owner,
        package=Subscription.Package.TRIAL,
        billing_period=None,
        status=Subscription.STATUS_TRIALING,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=14),
    )

class UserRegisterView(View):
    template_name = "app/uzytkownik/register.html"

    def get(self, request):
        request.session[REGISTRATION_STARTED_SESSION_KEY] = timezone.now().timestamp()
        user_form = UserRegistrationForm(prefix="user")
        company_form = CompanyForm(prefix="company")

        context = {
            "user_form": user_form,
            "company_form": company_form,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        if self._looks_like_bot(request):
            messages.error(
                request,
                json.dumps({
                    "body": "Nie udało się zweryfikować formularza. Spróbuj ponownie.",
                    "title": "Błąd weryfikacji",
                })
            )
            return redirect("register")

        user_form = UserRegistrationForm(request.POST, prefix="user")
        company_form = CompanyForm(request.POST, prefix="company")

        try:
            forms_valid = user_form.is_valid() and company_form.is_valid()
        except Exception as exc:
            _log_sanitized_registration_exception(exc)
            raise

        if forms_valid:
            if not settings.EMAIL_HOST:
                logger.error("Registration unavailable because the SMTP host is not configured")
                messages.error(
                    request,
                    "Rejestracja jest chwilowo niedostępna, ponieważ nie skonfigurowano wysyłki wiadomości aktywacyjnych.",
                )
                return render(
                    request,
                    self.template_name,
                    {"user_form": user_form, "company_form": company_form},
                )
            try:
                with transaction.atomic():
                    user = user_form.save()

                    addr = Address.objects.create(
                        street=company_form.cleaned_data.get("street", ""),
                        postcode=company_form.cleaned_data.get("postcode", ""),
                        city=company_form.cleaned_data.get("city", ""),
                        country="Polska",
                    )

                    company = company_form.save(commit=False)
                    company.main_address = addr
                    company.is_active = True
                    company.save()

                    user.company = company
                    user.role = user.Role.OWNER
                    user.save()

                    create_trial_subscription(company, user)
                    send_activation_email(request, user)
            except (OSError, SMTPException):
                # Do not leave a partial account if activation mail cannot be sent.
                logger.error("Registration rolled back because activation email delivery failed")
                messages.error(
                    request,
                    "Rejestracja jest chwilowo niedostępna, ponieważ nie można wysłać wiadomości aktywacyjnej. Spróbuj ponownie później.",
                )
                return render(
                    request,
                    self.template_name,
                    {"user_form": user_form, "company_form": company_form},
                )
            except Exception as exc:
                _log_sanitized_registration_exception(exc)
                raise

            messages.success(
                request,
                json.dumps({
                    'body': f"Pomyślnie zarejestrowano użytkownika {user.email}. Na adres e-mail otrzymałeś link do aktywacji konta",
                    'title': "Rejestracja zakończona!"
                })
            )

            return redirect("dashboard")
       
                # Obsługa błędów formularza
        for form in [user_form, company_form]:
            for field_name, error_list in form.errors.as_data().items():
                for error in error_list:
                    messages.error(
                        request,
                        json.dumps({
                            'body': str(error.message).capitalize(),
                            'title': "Błąd"
                        })
                    )

        # jeśli błędy – wracamy z tymi samymi formami
        context = {
            "user_form": user_form,
            "company_form": company_form,
        }
        return render(request, self.template_name, context)

    def _looks_like_bot(self, request):
        if request.POST.get("registration_website"):
            return True

        started_at = request.session.get(REGISTRATION_STARTED_SESSION_KEY)
        try:
            elapsed = timezone.now().timestamp() - float(started_at)
        except (TypeError, ValueError):
            return True

        return elapsed < REGISTRATION_MIN_SECONDS
