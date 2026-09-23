from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q

from app.pojazd.models import Vehicle
from app.pojazd.forms import VehicleEventForm
from app.pojazd.permissions import can_edit_vehicle, can_delete_vehicle, can_create_vehicle


class VehicleListView(LoginRequiredMixin, ListView):
    model = Vehicle
    template_name = "app/pojazd/vehicle_list.html"
    context_object_name = "vehicles"
    paginate_by = 10

    def get_paginate_by(self, queryset):
        try:
            return int(self.request.GET.get("per_page", 25))
        except (TypeError, ValueError):
            return 25

    def get_queryset(self):
        qs = Vehicle.objects.filter(
            company=self.request.user.company
        )

        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()

        if q:
            qs = qs.filter(
                Q(registration_number__icontains=q) |
                Q(brand__icontains=q) |
                Q(model__icontains=q) |
                Q(vin__icontains=q)
            )

        if status == "active":
            qs = qs.filter(is_active=True)

        elif status == "inactive":
            qs = qs.filter(is_active=False)

        return qs.order_by("registration_number")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["event_form"] = VehicleEventForm()
        context["can_edit_vehicle"] = can_edit_vehicle(self.request.user)
        context["can_delete_vehicle"] = can_delete_vehicle(self.request.user)
        context["can_create_vehicle"] = can_create_vehicle(self.request.user)

        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_per_page"] = self.request.GET.get("per_page", "25")

        return context
