from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib import messages

from app.oferta_praca.models import Offer


class OfferDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        offer = get_object_or_404(
            Offer,
            pk=pk,
            company=request.user.company,
        )
        offer.delete()
        messages.success(request, "Oferta została usunięta.")
        return redirect("offer_list")