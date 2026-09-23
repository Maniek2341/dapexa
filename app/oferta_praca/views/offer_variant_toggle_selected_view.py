from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.utils import timezone

from app.oferta_praca.models import OfferVariant, OfferActivity


class OfferVariantToggleSelectedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        variant = get_object_or_404(
            OfferVariant.objects.select_related("offer"),
            pk=pk,
            company=request.user.company,
        )

        variant.is_selected = not variant.is_selected
        variant.selected_at = timezone.now() if variant.is_selected else None
        variant.save(update_fields=["is_selected", "selected_at"])

        OfferActivity.objects.create(
            company=variant.offer.company,
            offer=variant.offer,
            type=OfferActivity.Type.VARIANT,
            title="Zmieniono wybór wariantu",
            description=(
                f"Wybrano wariant: {variant.name}"
                if variant.is_selected
                else f"Odznaczono wariant: {variant.name}"
            ),
            created_by=request.user,
        )

        return redirect("offer_detail", pk=variant.offer.pk)