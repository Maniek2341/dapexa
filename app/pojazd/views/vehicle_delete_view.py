from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.core.exceptions import PermissionDenied
from app.pojazd.permissions import can_delete_vehicle

from app.pojazd.models import Vehicle


class VehicleDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not can_delete_vehicle(request.user):
            raise PermissionDenied
        vehicle = Vehicle.objects.filter(
            pk=pk,
            company=request.user.company,
        ).first()

        if not vehicle:
            messages.error(request, "Nie znaleziono pojazdu.")
            return redirect("vehicle_list")

        vehicle.delete()
        messages.success(request, "Pojazd został usunięty.")
        return redirect("vehicle_list")
