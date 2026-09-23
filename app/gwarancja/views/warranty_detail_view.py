from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from app.gwarancja.models import WarrantyClaim
from app.gwarancja.permissions import can_edit_warranty


class WarrantyDetailView(LoginRequiredMixin, DetailView):
    model = WarrantyClaim
    template_name = "app/gwarancja/warranty_detail.html"
    context_object_name = "claim"

    def get_queryset(self):
        return (
            WarrantyClaim.objects
            .filter(company=self.request.user.company)
            .select_related(
                "client",
                "location",
                "product",
                "created_by",
            )
            .prefetch_related(
                "attachments",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activities = self.object.activities.select_related("created_by")
        context["activities"] = activities
        context["activities_count"] = activities.count()
        context["can_edit_warranty"] = can_edit_warranty(self.request.user)

        return context
