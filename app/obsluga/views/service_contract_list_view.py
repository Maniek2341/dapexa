# app/obsluga/views/service_contract_list_view.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.views.generic import ListView

from app.obsluga.models import (
    ServiceContract,
    ServiceContractStatus,
)
from app.obsluga.permissions import (
    can_add_obsluga,
    can_delete_obsluga,
    can_edit_obsluga,
    can_manage_obsluga,
)


class ServiceContractListView(LoginRequiredMixin, ListView,):
    model = ServiceContract
    template_name = "app/obsluga/list.html"
    context_object_name = "contracts"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            ServiceContract.objects
            .filter(
                company=self.request.user.company
            )
            .select_related(
                "client",
                "location",
                "caretaker",
            )
            .annotate(
                assets_total=Count(
                    "assets",
                    distinct=True,
                ),
                visits_total=Count(
                    "visits",
                    distinct=True,
                ),
            )
            .order_by(
                "-created_at"
            )
        )

        q = self.request.GET.get("q")

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(client__name__icontains=q)
                | Q(location__name__icontains=q)
                | Q(description__icontains=q)
            )

        status = self.request.GET.get("status")

        if status:
            queryset = queryset.filter(
                status=status
            )

        contract_type = self.request.GET.get("type")

        if contract_type:
            queryset = queryset.filter(
                contract_type=contract_type
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_add_obsluga"] = can_add_obsluga(self.request.user)
        context["can_edit_obsluga"] = can_edit_obsluga(self.request.user)
        context["can_delete_obsluga"] = can_delete_obsluga(self.request.user)
        context["can_manage_obsluga"] = can_manage_obsluga(self.request.user)

        contracts = (
            ServiceContract.objects
            .filter(
                company=self.request.user.company
            )
        )
        active_contracts_count = contracts.filter(status=ServiceContractStatus.ACTIVE).count()
        context["active_contracts_count"] = active_contracts_count

        context["total_contracts"] = contracts.count()

        context["active_contracts"] = contracts.filter(
            status=ServiceContractStatus.ACTIVE
        ).count()

        context["paused_contracts"] = contracts.filter(
            status=ServiceContractStatus.PAUSED
        ).count()

        context["ended_contracts"] = contracts.filter(
            status=ServiceContractStatus.ENDED
        ).count()

        context["total_assets"] = sum(
            contract.assets.count()
            for contract in contracts
        )

        context["total_visits"] = sum(
            contract.visits.count()
            for contract in contracts
        )

        context["status_choices"] = (
            ServiceContractStatus.choices
        )

        return context
