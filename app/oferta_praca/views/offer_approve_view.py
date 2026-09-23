from django.views import View
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from app.oferta_praca.models import Offer, OfferActivity


class OfferApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        offer = get_object_or_404(
            Offer,
            pk=pk,
            company=request.user.company,
        )

        offer.approved_by_manager = True
        offer.approved_by = request.user
        offer.approved_at = timezone.now()
        offer.save(update_fields=[
            "approved_by_manager",
            "approved_by",
            "approved_at",
        ])

        OfferActivity.objects.create(
            company=offer.company,
            offer=offer,
            type=OfferActivity.Type.APPROVAL,
            title="Oferta zatwierdzona przez managera",
            description=f"Zatwierdził: {request.user.first_name} {request.user.last_name}".strip(),
            created_by=request.user,
        )

        messages.success(request, "Oferta została zatwierdzona.")
        return redirect("offer_detail", pk=offer.pk)