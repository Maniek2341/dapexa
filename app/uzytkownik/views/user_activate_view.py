from django.views import View
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from app.core.models import PanelUser

class UserActivateView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = PanelUser.objects.get(pk=uid)
        except Exception:
            user = None

        if user and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save(update_fields=["is_active"])

            messages.success(request, "Konto zostało aktywowane. Możesz się zalogować.")
            return redirect("login")

        messages.error(request, "Link aktywacyjny jest nieprawidłowy lub wygasł.")
        return redirect("login")