# app/offers/views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView

from app.klient.models import ClientLocation
from app.oferta_praca.forms import OfferCreateForm
from app.oferta_praca.models import Offer, OfferImage, OfferActivity
from app.dokument.models import DocumentFolder


class OfferCreateView(LoginRequiredMixin, CreateView):
    model = Offer
    form_class = OfferCreateForm
    template_name = "app/oferta_praca/offer_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.user.company
        return kwargs

    def form_valid(self, form):
        offer = form.save(commit=False)
        offer.company = self.request.user.company
        offer.issue_date = timezone.now().date()
        offer.status = Offer.STATUS_NOWE
        offer.priority = Offer.Priority.LOW
        offer.save()

        for image in self.request.FILES.getlist("images"):
            OfferImage.objects.create(
                company=self.request.user.company,
                offer=offer,
                file=image,
            )

        OfferActivity.objects.create(
            company=offer.company,
            offer=offer,
            type=OfferActivity.Type.SYSTEM,
            title="Oferta utworzona",
            description=f"Utworzono ofertę {offer.number}",
            created_by=self.request.user,
        )

        self.object = offer
        messages.success(self.request, "Oferta została dodana.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Popraw błędy w formularzu.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("offer_detail", kwargs={"pk": self.object.pk})


class OfferClientLocationsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        client_id = request.GET.get("client")
        if not client_id:
            return JsonResponse([], safe=False)

        locations = (
            ClientLocation.objects
            .filter(client_id=client_id, client__company=request.user.company)
            .order_by("name")
        )

        data = [
            {
                "id": loc.id,
                "name": getattr(loc, "name", str(loc)),
            }
            for loc in locations
        ]
        return JsonResponse(data, safe=False)