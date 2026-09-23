from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.gwarancja.models import WarrantyClaim


class WarrantyClaimMarkRepairedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        claim = get_object_or_404(
            WarrantyClaim,
            pk=pk,
            company=request.user.company,
        )

        claim.mark_repaired(user=request.user)

        messages.success(
            request,
            "Zgłoszenie oznaczono jako naprawione."
        )

        return redirect("warranty_detail", pk=claim.pk)