from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from django.utils import timezone
from app.obsluga.services.periods import get_contract_current_period

from app.obsluga.models import ServiceContract
from app.obsluga.forms import ServiceContractAssetForm, ServiceContractParameterForm, ServiceContractMediaForm
from app.obsluga.permissions import has_obsluga_permission


class ServiceContractDetailView(LoginRequiredMixin, DetailView):
    model = ServiceContract
    template_name = "app/obsluga/detail.html"
    context_object_name = "contract"

    def get_queryset(self):
        return (
            ServiceContract.objects
            .filter(company=self.request.user.company)
            .select_related(
                "client",
                "location",
                "caretaker",
                "created_by",
            )
            .prefetch_related(
                "assets",
                "parameters",
                "people",
                "visits",
                "visits__checklist_items",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["assets"] = self.object.assets.all()
        context["parameters"] = self.object.parameters.all()
        context["people"] = self.object.people.all()
        context["visits"] = self.object.visits.all()
        context["asset_form"] = ServiceContractAssetForm()
        context["parameter_form"] = ServiceContractParameterForm()
        context["can_edit_obsluga"] = has_obsluga_permission(
            self.request.user, "service_contract_update"
        )
        context["can_asset_add"] = has_obsluga_permission(
            self.request.user, "service_contract_asset_add"
        )
        context["can_asset_edit"] = has_obsluga_permission(
            self.request.user, "service_contract_asset_update"
        )
        context["can_asset_delete"] = has_obsluga_permission(
            self.request.user, "service_contract_asset_delete"
        )
        context["can_parameter_add"] = has_obsluga_permission(
            self.request.user, "service_contract_parameter_add"
        )
        context["can_parameter_edit"] = has_obsluga_permission(
            self.request.user, "service_contract_parameter_update"
        )
        context["can_parameter_delete"] = has_obsluga_permission(
            self.request.user, "service_contract_parameter_delete"
        )
        context["can_visit_confirm"] = has_obsluga_permission(
            self.request.user, "service_visit_confirm_period"
        )

        period_start, period_end = get_contract_current_period(
            self.object,
            today=timezone.localdate(),
        )

        context["media"] = self.object.media.select_related(
            "uploaded_by"
        ).all()

        context["media_form"] = ServiceContractMediaForm()

        current_period_visit = self.object.visits.filter(
            period_start=period_start,
            period_end=period_end,
        ).select_related("performed_by").first()

        context["period_start"] = period_start
        context["period_end"] = period_end
        context["current_period_visit"] = current_period_visit

        context["activities"] = (
            self.object.activities
            .select_related("created_by")
            .order_by("-created_at")[:50]
        )

        return context
