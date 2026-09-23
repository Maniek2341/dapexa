from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.gwarancja.models import WarrantyClaim


class WarrantyClaimMarkReportedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        claim = get_object_or_404(
            WarrantyClaim,
            pk=pk,
            company=request.user.company,
        )

        external_number = request.POST.get("external_number", "").strip()

        if not external_number:
            messages.error(request, "Podaj numer zgłoszenia zewnętrznego.")
            return redirect("warranty_detail", pk=claim.pk)

        claim.mark_reported(
            user=request.user,
            external_number=external_number,
        )

        messages.success(request, "Zgłoszenie oznaczono jako zgłoszone.")
        return redirect("warranty_detail", pk=claim.pk)