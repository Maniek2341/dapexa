# app/clients/views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views import View

from app.core.models import Address
from app.klient.models import Client, ClientActivity, ContactPerson
from app.klient.forms import ClientForm
from app.klient.permissions import can_manage_clients


class KlientEditView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może edytować klientów.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, request, pk):
        return get_object_or_404(Client, pk=pk, company=request.user.company)

    def get_initial_from_instance(self, client: Client):
        shipping = client.shipping_address
        billing = client.billing_address

        billing_other = bool(
            billing and shipping and getattr(billing, "id", None) != getattr(shipping, "id", None)
        )

        # (w tej wersji nadal: jedna osoba kontaktowa = pierwsza)
        contact = (
            ContactPerson.objects.filter(client=client, company=client.company)
            .order_by("id")
            .first()
        )

        initial = {
            "client_type": client.client_type,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "name": client.name,
            "nip": client.nip,
            "email": client.email,
            "phone": client.phone,
            "caretaker": client.caretaker_id,
            "notes": client.notes,

            "shipping_street": street_name(shipping.street) if shipping else "",
            "shipping_street_no": street_no(shipping.street) if shipping else "",
            "shipping_zip": shipping.postcode if shipping else "",
            "shipping_city": shipping.city if shipping else "",
            "shipping_country": shipping.country if shipping else "Polska",

            "billing_other": billing_other,
            "billing_street": street_name(billing.street) if billing_other and billing else "",
            "billing_street_no": street_no(billing.street) if billing_other and billing else "",
            "billing_zip": billing.postcode if billing_other and billing else "",
            "billing_city": billing.city if billing_other and billing else "",
            "billing_country": billing.country if billing_other and billing else "Polska",
        }

        if contact:
            initial.update({
                "contact_first_name": contact.first_name,
                "contact_last_name": contact.last_name,
                "contact_email": contact.email,
                "contact_phone": contact.phone,
            })
        else:
            initial.update({
                "contact_first_name": "",
                "contact_last_name": "",
                "contact_email": "",
                "contact_phone": "",
            })

        return initial

    def get(self, request, pk):
        if not getattr(request.user, "company_id", None):
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        client = self.get_object(request, pk)
        form = ClientForm(user=request.user, initial=self.get_initial_from_instance(client))
        return render(request, "app/klient/edit.html", {"form": form, "client": client})

    def post(self, request, pk):
        if not getattr(request.user, "company_id", None):
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        client = self.get_object(request, pk)
        company = request.user.company

        # snapshot BEFORE (do historii)
        before = snapshot_client(client)

        form = ClientForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(request, "app/klient/edit.html", {"form": form, "client": client})

        cd = form.cleaned_data

        # 1) UPDATE shipping
        shipping_street_full = f"{(cd.get('shipping_street') or '').strip()} {(cd.get('shipping_street_no') or '').strip()}".strip()

        if client.shipping_address_id:
            shipping_address = client.shipping_address
            shipping_address.street = shipping_street_full
            shipping_address.postcode = (cd.get("shipping_zip") or "").strip()
            shipping_address.city = (cd.get("shipping_city") or "").strip()
            shipping_address.country = (cd.get("shipping_country") or "").strip() or "Polska"
            shipping_address.save()
        else:
            shipping_address = Address.objects.create(
                street=shipping_street_full,
                postcode=(cd.get("shipping_zip") or "").strip(),
                city=(cd.get("shipping_city") or "").strip(),
                country=(cd.get("shipping_country") or "").strip() or "Polska",
            )

        # 2) UPDATE billing
        billing_other = cd.get("billing_other")

        if billing_other:
            billing_street_full = f"{(cd.get('billing_street') or '').strip()} {(cd.get('billing_street_no') or '').strip()}".strip()
            billing_zip = (cd.get("billing_zip") or "").strip()
            billing_city = (cd.get("billing_city") or "").strip()

            # jeśli ktoś zaznaczył, ale nie podał – fallback do shipping
            if not (billing_street_full and billing_zip and billing_city):
                # jeśli wcześniej był osobny billing -> sprzątamy w obrębie firmy
                if client.billing_address_id and client.billing_address_id != client.shipping_address_id:
                    safe_delete_address(company_id=company.id, address_id=client.billing_address_id)
                billing_address = shipping_address
            else:
                if (not client.billing_address_id) or (client.billing_address_id == client.shipping_address_id):
                    billing_address = Address.objects.create(
                        street=billing_street_full,
                        postcode=billing_zip,
                        city=billing_city,
                        country=(cd.get("billing_country") or "").strip() or "Polska",
                    )
                else:
                    billing_address = client.billing_address
                    billing_address.street = billing_street_full
                    billing_address.postcode = billing_zip
                    billing_address.city = billing_city
                    billing_address.country = (cd.get("billing_country") or "").strip() or "Polska"
                    billing_address.save()
        else:
            if client.billing_address_id and client.billing_address_id != client.shipping_address_id:
                safe_delete_address(company_id=company.id, address_id=client.billing_address_id)
            billing_address = shipping_address

        # 3) UPDATE klient
        client.company = company
        client.client_type = cd.get("client_type")
        client.first_name = (cd.get("first_name") or "").strip()
        client.last_name = (cd.get("last_name") or "").strip()
        client.name = (cd.get("name") or "").strip()
        client.nip = (cd.get("nip") or "").strip()
        client.email = (cd.get("email") or "").strip()
        client.phone = (cd.get("phone") or "").strip()
        client.caretaker_id = cd.get("caretaker").id if cd.get("caretaker") else None
        client.notes = cd.get("notes") or ""
        client.shipping_address = shipping_address
        client.billing_address = billing_address
        client.save()

        # 4) UPDATE osoba kontaktowa (w tej wersji: jedna)
        if client.client_type == Client.TYPE_COMPANY:
            cf = (cd.get("contact_first_name") or "").strip()
            cl = (cd.get("contact_last_name") or "").strip()
            ce = (cd.get("contact_email") or "").strip()
            cp = (cd.get("contact_phone") or "").strip()
            has_any = cf or cl or ce or cp

            contact = (
                ContactPerson.objects.filter(client=client, company=company)
                .order_by("id")
                .first()
            )

            if has_any:
                if contact:
                    contact.first_name = cf
                    contact.last_name = cl
                    contact.email = ce
                    contact.phone = cp
                    contact.save()
                else:
                    ContactPerson.objects.create(
                        company=company,
                        client=client,
                        first_name=cf,
                        last_name=cl,
                        email=ce,
                        phone=cp,
                    )
            else:
                if contact:
                    contact.delete()
        else:
            ContactPerson.objects.filter(client=client, company=company).delete()

        # snapshot AFTER + diff -> historia
        after = snapshot_client(client)
        diff_text = diff_snapshots(before, after)

        ClientActivity.objects.create(
            company=company,
            client=client,
            created_by=request.user,
            type=ClientActivity.Type.KLIENT,
            title="Edytowano klienta",
            description=diff_text or "Zapisano bez zmian.",
        )

        messages.success(request, "Klient został zaktualizowany.")
        return redirect("klient_detail", pk=client.pk)


# -------------------------
# Pomocnicze funkcje
# -------------------------

def street_name(street_full: str):
    if not street_full:
        return ""
    parts = street_full.strip().split(" ")
    if len(parts) <= 1:
        return street_full.strip()
    return " ".join(parts[:-1])

def street_no(street_full: str):
    if not street_full:
        return ""
    parts = street_full.strip().split(" ")
    if len(parts) <= 1:
        return ""
    return parts[-1]

def safe_delete_address(*, company_id: int, address_id: int):
    """
    Usuwa adres tylko jeśli NIE jest używany przez żadnego klienta w tej firmie.
    (Bezpieczniej niż globalnie.)
    """
    in_use = Client.objects.filter(company_id=company_id, shipping_address_id=address_id).exists() or \
             Client.objects.filter(company_id=company_id, billing_address_id=address_id).exists()
    if not in_use:
        Address.objects.filter(id=address_id).delete()

def snapshot_client(client: Client) -> dict:
    ship = client.shipping_address
    bill = client.billing_address
    return {
        "client_type": client.client_type,
        "first_name": client.first_name,
        "last_name": client.last_name,
        "name": client.name,
        "nip": client.nip,
        "email": client.email,
        "phone": client.phone,
        "caretaker_id": client.caretaker_id,
        "notes": client.notes,
        "shipping": format_addr(ship),
        "billing": format_addr(bill),
        "is_active": client.is_active,
    }

def format_addr(addr: Address) -> str:
    if not addr:
        return ""
    return f"{addr.street}|{addr.postcode}|{addr.city}|{addr.country}"

def diff_snapshots(before: dict, after: dict) -> str:
    labels = {
        "client_type": "Typ",
        "first_name": "Imię",
        "last_name": "Nazwisko",
        "name": "Nazwa",
        "nip": "NIP",
        "email": "E-mail",
        "phone": "Telefon",
        "caretaker_id": "Opiekun",
        "notes": "Notatki",
        "shipping": "Adres serwisowy",
        "billing": "Adres rozliczeniowy",
        "is_active": "Aktywny",
    }
    lines = []
    for k in labels.keys():
        if before.get(k) != after.get(k):
            lines.append(f"{labels[k]}: „{before.get(k)}” → „{after.get(k)}”")
    return "\n".join(lines)
