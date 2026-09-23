from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages

from app.klient.models import Client, ClientActivity
from app.klient.permissions import can_manage_clients


class KlientActivateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może przywracać klientów.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        if not hasattr(request.user, "company") or request.user.company is None:
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        client = get_object_or_404(
            Client,
            pk=pk,
            company=request.user.company
        )

        if client.is_active:
            messages.info(request, "Klient jest już aktywny.")
            return redirect("klient_archive")

        client.is_active = True
        client.save(update_fields=["is_active"])

        # ✅ HISTORIA
        display_name = (
            client.name
            or f"{client.first_name} {client.last_name}".strip()
            or f"Klient #{client.pk}"
        )

        ClientActivity.objects.create(
            company=request.user.company,
            client=client,
            created_by=request.user,
            type=ClientActivity.Type.STATUS,
            title="Przywrócono klienta",
            description=f"Przywrócono z archiwum: {display_name}",
        )

        messages.success(request, "Klient został przywrócony.")
        return redirect("klient_archive")
