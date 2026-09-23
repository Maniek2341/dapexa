from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views import View

from app.klient.models import Client, ContactPerson, ClientActivity
from app.klient.permissions import can_manage_clients


class KlientDeactivateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może archiwizować klientów.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, request, pk):
        return get_object_or_404(Client, pk=pk, company=request.user.company)

    def get(self, request, pk):
        if not hasattr(request.user, "company") or request.user.company is None:
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        client = self.get_object(request, pk)
        return render(request, "app/klient/deactivate.html", {"client": client})

    def post(self, request, pk):
        if not hasattr(request.user, "company") or request.user.company is None:
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        client = self.get_object(request, pk)

        if not client.is_active:
            messages.info(request, "Ten klient jest już dezaktywowany.")
            return redirect("klient")

        client.is_active = False
        client.save(update_fields=["is_active"])

        # opcjonalnie: jeśli ContactPerson ma is_active
        try:
            ContactPerson.objects.filter(client=client, company=client.company).update(is_active=False)
        except Exception:
            pass

        # ✅ HISTORIA (ClientActivity)
        display_name = client.name or f"{client.first_name} {client.last_name}".strip() or f"Klient #{client.pk}"

        ClientActivity.objects.create(
            company=request.user.company,
            client=client,
            created_by=request.user,
            type=ClientActivity.Type.KLIENT,  # albo OTHER jeśli wolisz
            title="Dezaktywowano klienta",
            description=f"Przeniesiono do archiwum: {display_name}",
        )

        messages.success(request, "Klient został dezaktywowany.")
        return redirect("klient")
