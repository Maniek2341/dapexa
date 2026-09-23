from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views import View

from app.core.models import Address
from app.klient.models import Client, ContactPerson
from app.klient.permissions import can_manage_clients


class KlientDeleteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może usuwać klientów.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, request, pk):
        return get_object_or_404(Client, pk=pk, company=request.user.company)

    def get(self, request, pk):
        if not hasattr(request.user, "company") or request.user.company is None:
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        client = self.get_object(request, pk)
        return render(request, "app/klient/delete.html", {"client": client})

    def post(self, request, pk):
        if not hasattr(request.user, "company") or request.user.company is None:
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        client = self.get_object(request, pk)

        shipping_id = client.shipping_address_id
        billing_id = client.billing_address_id

        # 1) Usuń osoby kontaktowe tego klienta (jeśli są)
        ContactPerson.objects.filter(client=client, company=client.company).delete()

        # 2) Usuń klienta
        client.delete()

        # 3) Sprzątanie adresów (tylko jeśli nie są używane gdzie indziej)
        # billing osobny
        if billing_id and billing_id != shipping_id:
            safe_delete_address_if_unused(billing_id)

        # shipping
        if shipping_id:
            safe_delete_address_if_unused(shipping_id)

        messages.success(request, "Klient został usunięty.")
        return redirect("klient")


def safe_delete_address_if_unused(address_id: int):
    # usuwa adres tylko jeśli nie jest używany przez innych klientów
    used_as_shipping = Client.objects.filter(shipping_address_id=address_id).exists()
    used_as_billing = Client.objects.filter(billing_address_id=address_id).exists()

    if not (used_as_shipping or used_as_billing):
        Address.objects.filter(id=address_id).delete()
