# app/clients/views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View

from app.core.models import Address
from app.klient.models import Client, ClientActivity, ContactPerson
from app.klient.forms import ClientForm
from app.klient.permissions import can_manage_clients


class KlientAddView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może dodawać klientów.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        # jeśli w __init__ ClientForm przyjmujesz usera, to tak:
        form = ClientForm(user=request.user)
        # jeśli nie – po prostu: form = ClientForm()
        context = {
            "form": form,
        }
        return render(request, 'app/klient/add.html', context)

    def post(self, request):
        if not hasattr(request.user, "company") or request.user.company is None:
            messages.error(request, "Nie można utworzyć klienta – użytkownik nie jest przypisany do firmy.")
            return redirect("klient")

        form = ClientForm(request.POST, user=request.user)

        if not form.is_valid():
            # <- tu wracasz z błędami, wtedy „coś się dzieje”
            return render(request, "app/klient/add.html", {"form": form})

        # ✅ zapis klienta + adresów przez ClientForm.save()
        client = form.save(company=request.user.company)

        cd = form.cleaned_data

        # ✅ osoba kontaktowa (z pól contact_* z template)
        if cd.get("client_type") == Client.TYPE_COMPANY:
            contact_first_name = (cd.get("contact_first_name") or "").strip()
            contact_last_name = (cd.get("contact_last_name") or "").strip()
            contact_email = (cd.get("contact_email") or "").strip()
            contact_phone = (cd.get("contact_phone") or "").strip()

            if contact_first_name or contact_last_name or contact_email or contact_phone:
                ContactPerson.objects.create(
                    company=request.user.company,
                    client=client,
                    first_name=contact_first_name,
                    last_name=contact_last_name,
                    email=contact_email,
                    phone=contact_phone,
                )
        
            # ✅ 1 wpis do historii (bez KLIENT, bo nie istnieje)
        display_name = client.name or f"{client.first_name} {client.last_name}".strip() or f"Klient #{client.pk}"

        ClientActivity.objects.create(
            company=request.user.company,
            client=client,
            created_by=request.user,
            type=ClientActivity.Type.KLIENT,
            title="Dodano klienta",
            description=display_name,
        )

        messages.success(request, "Klient został pomyślnie dodany.")
        return redirect("klient")
