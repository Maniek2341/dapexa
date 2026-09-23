from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from app.gwarancja.models import WarrantyClaim
from app.gwarancja.permissions import can_delete_warranty
from django.core.exceptions import PermissionDenied


class WarrantyClaimDeleteView(LoginRequiredMixin, DeleteView):
    model = WarrantyClaim
    success_url = reverse_lazy("warranty_claim_list")

    def get_queryset(self):
        return WarrantyClaim.objects.filter(
            company=self.request.user.company
        )

    def dispatch(self, request, *args, **kwargs):
        if not can_delete_warranty(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
