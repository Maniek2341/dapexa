from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib import messages

from app.pojazd.models import (
    VehicleEvent,
    VehicleChangeHistory,
)
from app.pojazd.forms import VehicleEventForm


class VehicleEventUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):

        event = get_object_or_404(
            VehicleEvent,
            pk=pk,
            company=request.user.company,
        )

        form = VehicleEventForm(
            request.POST,
            request.FILES,
            instance=event,
        )

        if form.is_valid():

            updated_event = form.save()

            VehicleChangeHistory.objects.create(
                company=request.user.company,
                vehicle=updated_event.vehicle,
                event=updated_event,
                action=VehicleChangeHistory.Action.EVENT_UPDATED,
                changed_by=request.user,
                description=f"Zaktualizowano zdarzenie: {updated_event.title}",
            )

            messages.success(
                request,
                "Zdarzenie zostało zaktualizowane."
            )

        else:
            messages.error(
                request,
                "Nie udało się zapisać zmian."
            )

        return redirect(
            "vehicle_detail",
            pk=event.vehicle.pk
        )