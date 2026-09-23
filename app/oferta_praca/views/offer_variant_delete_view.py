from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.oferta_praca.models import OfferVariant, OfferActivity


class OfferVariantDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        variant = get_object_or_404(
            OfferVariant.objects.select_related("offer"),
            pk=pk,
            company=request.user.company,
        )

        # 🔥 zapisz dane PRZED usunięciem
        offer = variant.offer
        variant_name = variant.name

        variant.delete()

        OfferActivity.objects.create(
            company=offer.company,
            offer=offer,
            type=OfferActivity.Type.VARIANT,
            title="Usunięto wariant",
            description=f"Usunięto wariant: {variant_name} | wartość: {variant.total_netto} zł",
            created_by=request.user,
        )

        return redirect("offer_detail", pk=offer.pk)