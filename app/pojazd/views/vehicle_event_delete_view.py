from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.pojazd.models import (
    VehicleEvent,
    VehicleChangeHistory,
)


class VehicleEventDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):

        event = get_object_or_404(
            VehicleEvent,
            pk=pk,
            company=request.user.company,
        )

        vehicle = event.vehicle
        vehicle_pk = vehicle.pk

        event_description = event.description

        VehicleChangeHistory.objects.create(
            company=request.user.company,
            vehicle=vehicle,
            event=event,
            action=VehicleChangeHistory.Action.EVENT_DELETED,
            changed_by=request.user,
            description=f"Usunięto zdarzenie: {event_description}",
        )

        event.delete()

        messages.success(
            request,
            "Zdarzenie zostało usunięte."
        )

        return redirect(
            "vehicle_detail",
            pk=vehicle_pk
        )