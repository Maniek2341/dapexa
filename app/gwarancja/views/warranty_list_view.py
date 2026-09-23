# app/warranties/views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from app.gwarancja.models import WarrantyClaim, WarrantyClaimStatus
from app.gwarancja.permissions import can_delete_warranty, can_edit_warranty


class WarrantyListView(LoginRequiredMixin, ListView):
    model = WarrantyClaim
    template_name = "app/gwarancja/warranty_list.html"
    context_object_name = "claims"
    paginate_by = 25

    def get_queryset(self):
        qs = WarrantyClaim.objects.filter(
            company=self.request.user.company
        ).select_related(
            "client",
            "location",
            "product",
            "created_by",
        )

        status = self.request.GET.get("status")
        search = self.request.GET.get("q")

        if status:
            qs = qs.filter(status=status)

        if search:
            qs = qs.filter(
                Q(external_number__icontains=search)
                | Q(provider__icontains=search)
                | Q(client__name__icontains=search)
                | Q(product__name__icontains=search)
                | Q(fault_description__icontains=search)
            )

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["statuses"] = WarrantyClaimStatus.choices
        context["selected_status"] = self.request.GET.get("status", "")
        context["search"] = self.request.GET.get("q", "")
        context["can_delete_warranty"] = can_delete_warranty(self.request.user)
        context["can_edit_warranty"] = can_edit_warranty(self.request.user)

        return context
