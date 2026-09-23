from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView
from django.contrib import messages
from django.shortcuts import redirect

from app.pojazd.models import (
    Vehicle,
    VehicleChangeHistory,
)
from app.pojazd.forms import VehicleForm
from django.core.exceptions import PermissionDenied
from app.pojazd.permissions import can_create_vehicle


class VehicleCreateView(LoginRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "app/pojazd/vehicle_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_create_vehicle(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):

        vehicle = form.save(commit=False)

        vehicle.company = self.request.user.company

        vehicle.save()

        VehicleChangeHistory.objects.create(
            company=self.request.user.company,
            vehicle=vehicle,
            action=VehicleChangeHistory.Action.CREATED,
            changed_by=self.request.user,
            description=f"Utworzono pojazd: {vehicle.registration_number}",
        )

        messages.success(
            self.request,
            "Pojazd został dodany."
        )

        return redirect("vehicle_list")
