from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views import View

from app.klient.models import ClientLocation, ClientActivity


class LocationDeleteView(LoginRequiredMixin, View):

    def post(self, request, location_id):

        location = get_object_or_404(
            ClientLocation,
            pk=location_id,
            company=request.user.company
        )

        client = location.client
        name = location.name or "Lokalizacja"

        # usuń adres jeśli istnieje
        if location.address_id:
            location.address.delete()

        location.delete()

        # historia
        ClientActivity.objects.create(
            company=request.user.company,
            client=client,
            created_by=request.user,
            type=ClientActivity.Type.KLIENT,
            title="Usunięto lokalizację",
            description=name,
        )

        messages.success(request, "Lokalizacja została usunięta.")

        return redirect("klient_detail", pk=client.pk)