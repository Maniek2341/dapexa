from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from app.pojazd.models import Vehicle, VehicleChangeHistory
from app.pojazd.forms import VehicleEventForm
from app.pojazd.permissions import can_edit_vehicle, can_delete_vehicle

class VehicleDetailView(LoginRequiredMixin, DetailView):
    model = Vehicle
    template_name = "app/pojazd/vehicle_detail.html"
    context_object_name = "vehicle"

    def get_queryset(self):
        return Vehicle.objects.filter(company=self.request.user.company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["events"] = self.object.events.all().order_by("-event_date", "-created_at")
        context["history"] = self.object.change_history.select_related(
            "changed_by",
            "event",
        ).all().order_by("-changed_at")
        context["event_form"] = VehicleEventForm()
        context["can_edit_vehicle"] = can_edit_vehicle(self.request.user)
        context["can_delete_vehicle"] = can_delete_vehicle(self.request.user)
        return context
