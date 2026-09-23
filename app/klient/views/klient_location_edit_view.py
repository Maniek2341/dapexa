# app/klient/views/location_edit_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.core.models import Address
from app.klient.models import ClientActivity, ClientLocation, ContactPerson


class LocationEditView(LoginRequiredMixin, View):

    @transaction.atomic
    def post(self, request, location_id):
        location = get_object_or_404(
            ClientLocation,
            pk=location_id,
            company=request.user.company,
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

        is_default = request.POST.get("is_default") == "on"
        is_active = request.POST.get("is_active") == "on"

        contact_person = None
        if contact_person_id:
            contact_person = ContactPerson.objects.filter(
                pk=contact_person_id,
                company=request.user.company,
                client=location.client,
            ).first()

        if is_default:
            ClientLocation.objects.filter(
                client=location.client,
                company=request.user.company,
                is_default=True,
            ).exclude(pk=location.pk).update(is_default=False)

        location.name = name
        location.code = code
        location.notes = notes
        location.contact_person = contact_person
        location.is_default = is_default
        location.is_active = is_active

        if street or street_no or zip_code or city:
            if location.address:
                address = location.address
                address.street = street
                address.street_no = street_no
                address.postcode = zip_code
                address.city = city
                address.country = country

                try:
                    address.save()
                except ValidationError:
                    Address.objects.filter(pk=address.pk).update(
                        street=street,
                        street_no=street_no,
                        postcode=zip_code,
                        city=city,
                        country=country,
                        latitude=None,
                        longitude=None,
                    )

                    messages.warning(
                        request,
                        "Lokalizacja została zaktualizowana, ale nie udało się ustalić współrzędnych adresu."
                    )
            else:
                try:
                    address = Address.objects.create(
                        street=street,
                        street_no=street_no,
                        postcode=zip_code,
                        city=city,
                        country=country,
                    )
                except ValidationError:
                    address = Address(
                        street=street,
                        street_no=street_no,
                        postcode=zip_code,
                        city=city,
                        country=country,
                        latitude=None,
                        longitude=None,
                    )
                    Address.objects.bulk_create([address])

                    messages.warning(
                        request,
                        "Lokalizacja została zaktualizowana, ale nie udało się ustalić współrzędnych adresu."
                    )

                location.address = address
        else:
            location.address = None

        location.save()

        ClientActivity.objects.create(
            company=request.user.company,
            client=location.client,
            type=ClientActivity.Type.OTHER,
            title="Zaktualizowano lokalizację",
            description=(
                f"Nazwa: {location.name or '-'}\n"
                f"Kod: {location.code or '-'}\n"
                f"Adres: {street or '-'}, {street_no or '-'}, {zip_code} {city}\n"
                f"Domyślna: {'Tak' if is_default else 'Nie'}\n"
                f"Aktywna: {'Tak' if is_active else 'Nie'}"
            ),
            related_app="klient",
            related_model="ClientLocation",
            related_id=str(location.pk),
            created_by=request.user,
        )

        messages.success(
            request,
            f"Lokalizacja '{location.name or 'Lokalizacja'}' została zaktualizowana."
        )

        return redirect("klient_detail", pk=location.client_id)