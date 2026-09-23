# app/klient/views/klient_location_add_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.core.models import Address
from app.klient.models import Client, ClientActivity, ClientLocation
from app.klient.permissions import can_manage_clients


class LocationAddView(LoginRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może dodawać lokalizacji klienta.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, client_id):
        user = request.user

        client = get_object_or_404(
            Client,
            pk=client_id,
            company=user.company,
        )

        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        street = request.POST.get("street", "").strip()
        street_no = request.POST.get("street_no", "").strip()
        zip_code = request.POST.get("zip_code", "").strip()
        city = request.POST.get("city", "").strip()
        country = request.POST.get("country", "").strip() or "Polska"
        notes = request.POST.get("notes", "").strip()
        contact_person_id = request.POST.get("contact_person") or None
        is_default = bool(request.POST.get("is_default"))

        address = None

        if street or zip_code or city:
            try:
                address = Address.objects.create(
                    street=f"{street} {street_no}".strip(),
                    postcode=zip_code,
                    city=city,
                    country=country,
                )
            except ValidationError:
                address = Address(
                    street=f"{street} {street_no}".strip(),
                    postcode=zip_code,
                    city=city,
                    country=country,
                    latitude=None,
                    longitude=None,
                )

                # omija Address.save(), żeby nie wywaliło błędu geokodowania
                Address.objects.bulk_create([address])

                messages.warning(
                    request,
                    "Lokalizacja została dodana, ale nie udało się ustalić współrzędnych adresu."
                )

        if is_default:
            ClientLocation.objects.filter(
                client=client,
                company=client.company,
                is_default=True,
            ).update(is_default=False)

        location = ClientLocation.objects.create(
            company=client.company,
            client=client,
            name=name,
            code=code,
            address=address,
            contact_person_id=contact_person_id,
            notes=notes,
            is_default=is_default,
            is_active=True,
        )

        address_text = "—"
        if address:
            address_text = f"{address.street}, {address.postcode} {address.city}".strip()

        ClientActivity.objects.create(
            company=client.company,
            client=client,
            type=ClientActivity.Type.OTHER,
            title="Dodano lokalizację",
            description=(
                f"{location.name or 'Lokalizacja'}"
                f"{' (domyślna)' if location.is_default else ''}"
                f"\nAdres: {address_text}"
            ),
            related_app="klient",
            related_model="ClientLocation",
            related_id=str(location.pk),
            created_by=user,
        )

        messages.success(request, "Lokalizacja została dodana.")

        return redirect("klient_detail", pk=client.pk)
