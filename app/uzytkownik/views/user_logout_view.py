import json

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.utils.translation import gettext as _


class UserLogoutView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        messages.info(request, json.dumps(
            {
                'body': _("Pomyślnie wylogowano, do zobaczenia później!"),
                'title': _("Pomyślnie wylogowano!")
            }
        ))

        logout(request)
        return redirect('login')
