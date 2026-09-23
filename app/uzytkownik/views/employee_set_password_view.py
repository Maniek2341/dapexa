from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.shortcuts import render, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View

from app.uzytkownik.forms import SettPasswordForm

User = get_user_model()

activation_token = PasswordResetTokenGenerator()


class EmployeeSetPasswordView(View):
    """
    Widok ustawienia hasła przez pracownika po kliknięciu linku aktywacyjnego.
    """

    def _get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=uid)
        except Exception:
            return None

    def get(self, request, uidb64, token):
        user = self._get_user(uidb64)

        if user is None or not activation_token.check_token(user, token):
            messages.error(
                request,
                "Link aktywacyjny jest nieprawidłowy lub wygasł."
            )
            return redirect("login")

        form = SettPasswordForm(user=user)
        return render(request, "app/pracownik/set_password.html", {
            "form": form,
            "uid": uidb64,
            "token": token,
            "employee": user,
        })

    def post(self, request, uidb64, token):
        user = self._get_user(uidb64)

        if user is None or not activation_token.check_token(user, token):
            messages.error(
                request,
                "Link aktywacyjny jest nieprawidłowy lub wygasł."
            )
            return redirect("login")

        form = SettPasswordForm(user=user, data=request.POST)

        if form.is_valid():
            form.save()

            # aktywuj konto
            user.is_active = True
            user.is_active_employee = True
            user.save(update_fields=["is_active", "is_active_employee"])

            messages.success(
                request,
                "Hasło zostało ustawione. Możesz się teraz zalogować."
            )
            return redirect("login")

        return render(request, "app/pracownik/set_password.html", {
            "form": form,
            "uid": uidb64,
            "token": token,
            "employee": user,
        })
