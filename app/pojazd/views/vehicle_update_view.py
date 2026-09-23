from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from app.pojazd.models import Vehicle, VehicleChangeHistory
from app.pojazd.forms import VehicleForm
from django.core.exceptions import PermissionDenied
from app.pojazd.permissions import can_edit_vehicle


class VehicleUpdateView(LoginRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "app/pojazd/vehicle_form.html"

    def get_queryset(self):
        if not can_edit_vehicle(self.request.user):
            raise PermissionDenied
        return Vehicle.objects.filter(company=self.request.user.company)

    def form_valid(self, form):
        response = super().form_valid(form)

        VehicleChangeHistory.objects.create(
            company=self.request.user.company,
            vehicle=self.object,
            action=VehicleChangeHistory.Action.UPDATED,
            changed_by=self.request.user,
            description="Zaktualizowano dane pojazdu.",
        )

        messages.success(self.request, "Pojazd został zaktualizowany.")
        return response

    def get_success_url(self):
        return reverse_lazy("vehicle_detail", kwargs={"pk": self.object.pk})
