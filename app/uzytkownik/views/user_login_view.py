import json
import secrets
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from app.core.models import PanelUser
from app.uzytkownik.forms import LoginForm, LoginTwoFactorForm


class UserLoginView(View):
    two_factor_session_user_key = "pending_2fa_user_id"
    two_factor_session_next_key = "pending_2fa_next"
    two_factor_session_remember_key = "pending_2fa_remember"

    def _safe_next_url(self, request, value):
        if value and url_has_allowed_host_and_scheme(
            url=value,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return value
        return str(reverse_lazy("dashboard"))

    def _clear_pending_two_factor(self, request):
        for key in (
            self.two_factor_session_user_key,
            self.two_factor_session_next_key,
            self.two_factor_session_remember_key,
        ):
            request.session.pop(key, None)

    def _send_two_factor_code(self, user):
        code = f"{secrets.randbelow(1_000_000):06d}"
        user.login_2fa_code_hash = make_password(code)
        user.login_2fa_expires_at = timezone.now() + timedelta(minutes=10)
        user.login_2fa_attempts = 0
        user.save(update_fields=[
            "login_2fa_code_hash",
            "login_2fa_expires_at",
            "login_2fa_attempts",
        ])

        body = (
            f"Cześć {user.first_name or user.email},\n\n"
            f"Twój kod logowania to: {code}\n\n"
            "Kod jest ważny przez 10 minut. Jeżeli to nie Ty próbujesz się zalogować, zmień hasło."
        )
        email = EmailMessage(
            subject="Kod weryfikacyjny logowania",
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.send(fail_silently=True)

    def _render_login(self, request, form=None, next_url="", email=""):
        return render(request, "app/uzytkownik/login.html", {
            "email": email,
            "next": next_url,
            "login_form": form or LoginForm(),
            "two_factor_form": LoginTwoFactorForm(),
            "two_factor_required": False,
        })

    def _render_two_factor(self, request, form=None):
        return render(request, "app/uzytkownik/login.html", {
            "next": request.session.get(self.two_factor_session_next_key, ""),
            "login_form": LoginForm(),
            "two_factor_form": form or LoginTwoFactorForm(),
            "two_factor_required": True,
        })

    def get(self, request):
        # Jeśli user już zalogowany – przekieruj (opcjonalne, ale zwykle wygodne)
        if request.user.is_authenticated:
            return redirect("dashboard")  # podmień na swój widok po zalogowaniu

        if request.GET.get("restart"):
            self._clear_pending_two_factor(request)

        if request.session.get(self.two_factor_session_user_key):
            return self._render_two_factor(request)

        next_url = request.GET.get("next", "")

        return self._render_login(
            request,
            next_url=self._safe_next_url(request, next_url) if next_url else "",
        )

    def post(self, request):
        if request.session.get(self.two_factor_session_user_key):
            return self._post_two_factor(request)

        form = LoginForm(request.POST)
        email = ""
        password = ""
        user = None

        if form.is_valid():
            email = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=email, password=password)

        next_url = self._safe_next_url(request, request.POST.get("next", ""))

        # Prosta walidacja czy pola wypełnione
        if not email or not password:
            messages.error(request, "Podaj adres e-mail i hasło.")
            return self._render_login(request, form=form, email=email, next_url=next_url)

        if user is not None:
            if user.is_active and (user.is_active_employee or user.is_superuser):
                if user.two_factor_enabled:
                    self._send_two_factor_code(user)
                    request.session[self.two_factor_session_user_key] = user.pk
                    request.session[self.two_factor_session_next_key] = next_url
                    request.session[self.two_factor_session_remember_key] = bool(request.POST.get("remember"))
                    messages.info(request, json.dumps({
                        "body": f"Wysłaliśmy 6-cyfrowy kod weryfikacyjny na adres {user.email}.",
                        "title": "Potwierdź logowanie"
                    }))
                    return self._render_two_factor(request)

                login(request, user)

                remember = request.POST.get("remember")
                if not remember:
                    request.session.set_expiry(0)  # sesja wygaśnie po zamknięciu przeglądarki

                messages.success(request, json.dumps({
                        'body': f"Pomyślnie zalogowano jako {email}",
                        'title': "Zalogowano!"
                    }))
                return HttpResponseRedirect(next_url)
            else:
                messages.error(request, json.dumps({
                        'body': "Twoje konto jest nieaktywne albo nie zostało aktywowane. Skontaktuj się z administratorem.",
                        'title': "Konto zablokowane"
                    }))
        else:
            messages.error(request, json.dumps({
                    'body': "Twój login lub hasło są nieprawidłowe, spróbuj ponownie!",
                    'title': "Brak autoryzacji!"
                }))

        # W razie błędu wracamy do formularza z wpisanym emailem
        return self._render_login(request, form=form, email=email, next_url=next_url)

    def _post_two_factor(self, request):
        user_id = request.session.get(self.two_factor_session_user_key)
        next_url = self._safe_next_url(
            request,
            request.session.get(self.two_factor_session_next_key, ""),
        )
        form = LoginTwoFactorForm(request.POST)

        try:
            user = PanelUser.objects.get(pk=user_id, is_active=True)
            if not user.is_superuser and not user.is_active_employee:
                raise PanelUser.DoesNotExist
        except PanelUser.DoesNotExist:
            self._clear_pending_two_factor(request)
            messages.error(request, "Sesja weryfikacji wygasła. Zaloguj się ponownie.")
            return redirect("login")

        if not form.is_valid():
            return self._render_two_factor(request, form=form)

        if (
            not user.login_2fa_code_hash
            or not user.login_2fa_expires_at
            or user.login_2fa_expires_at < timezone.now()
        ):
            self._clear_pending_two_factor(request)
            messages.error(request, "Kod weryfikacyjny wygasł. Zaloguj się ponownie.")
            return redirect("login")

        if user.login_2fa_attempts >= 5:
            self._clear_pending_two_factor(request)
            user.login_2fa_code_hash = ""
            user.login_2fa_expires_at = None
            user.login_2fa_attempts = 0
            user.save(update_fields=[
                "login_2fa_code_hash",
                "login_2fa_expires_at",
                "login_2fa_attempts",
            ])
            messages.error(request, "Przekroczono limit prób. Zaloguj się ponownie.")
            return redirect("login")

        code = form.cleaned_data["code"]
        if not check_password(code, user.login_2fa_code_hash):
            user.login_2fa_attempts += 1
            user.save(update_fields=["login_2fa_attempts"])
            messages.error(request, "Nieprawidłowy kod weryfikacyjny.")
            return self._render_two_factor(request, form=form)

        user.login_2fa_code_hash = ""
        user.login_2fa_expires_at = None
        user.login_2fa_attempts = 0
        user.save(update_fields=[
            "login_2fa_code_hash",
            "login_2fa_expires_at",
            "login_2fa_attempts",
        ])

        login(request, user)
        remember = request.session.get(self.two_factor_session_remember_key)
        self._clear_pending_two_factor(request)
        if not remember:
            request.session.set_expiry(0)

        messages.success(request, json.dumps({
            "body": f"Pomyślnie zalogowano jako {user.email}",
            "title": "Zalogowano!"
        }))
        return HttpResponseRedirect(next_url)
