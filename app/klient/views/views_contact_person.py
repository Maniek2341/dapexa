from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View

from app.klient.forms import ContactPersonCreateForm
from app.klient.models import Client, ContactPerson, ClientActivity
from app.klient.permissions import can_manage_clients


class ContactPersonAddView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może dodawać osób kontaktowych.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, client_pk):
        client = get_object_or_404(
            Client,
            pk=client_pk,
            company=request.user.company,
            is_active=True,
        )

        if client.client_type != Client.TYPE_COMPANY:
            messages.error(request, "Osoby kontaktowe można dodawać tylko dla klienta typu Firma.")
            return redirect("klient_detail", pk=client.pk)

        form = ContactPersonCreateForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Popraw błędy w formularzu osoby kontaktowej.")
            return redirect("klient_detail", pk=client.pk)

        cp = form.save(commit=False)
        cp.company = request.user.company
        cp.client = client
        cp.save()

        # ✅ historia klienta
        ClientActivity.objects.create(
            company=request.user.company,
            client=client,
            created_by=request.user,
            type=ClientActivity.Type.KLIENT,
            title="Dodano osobę kontaktową",
            description=f"{cp.first_name} {cp.last_name}".strip(),
        )

        messages.success(request, "Osoba kontaktowa została dodana.")
        return redirect("klient_detail", pk=client.pk)
