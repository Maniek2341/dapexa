from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from app.klient.models import Client
from app.klient.permissions import can_manage_clients


class KlientArchiveView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def get(self, request):
        if not hasattr(request.user, "company") or request.user.company is None:
            return render(request, "app/klient/archive.html", {"clients": []})

        clients = (
            Client.objects
            .filter(company=request.user.company, is_active=False)
            .order_by("client_type", "name", "last_name", "first_name")
        )

        return render(request, "app/klient/archive.html", {
            "clients": clients,
            "can_manage_clients": can_manage_clients(request.user),
        })
