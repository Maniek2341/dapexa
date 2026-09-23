from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.pojazd.models import (
    Vehicle,
    VehicleChangeHistory,
)
from app.pojazd.forms import VehicleEventForm


class VehicleEventCreateView(LoginRequiredMixin, View):
    def post(self, request, vehicle_pk):

        vehicle = get_object_or_404(
            Vehicle,
            pk=vehicle_pk,
            company=request.user.company,
        )

        form = VehicleEventForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            event = form.save(commit=False)

            event.company = request.user.company
            event.vehicle = vehicle
            event.created_by = request.user

            event.save()

            VehicleChangeHistory.objects.create(
                company=request.user.company,
                vehicle=vehicle,
                event=event,
                action=VehicleChangeHistory.Action.EVENT_CREATED,
                changed_by=request.user,
                description=f"Dodano zdarzenie: {event.description}",
            )

            messages.success(
                request,
                "Zdarzenie zostało dodane."
            )

            return redirect(
                "vehicle_detail",
                pk=vehicle.pk
            )

        messages.error(
            request,
            "Nie udało się dodać zdarzenia."
        )

        return redirect(
            "vehicle_detail",
            pk=vehicle.pk
        )