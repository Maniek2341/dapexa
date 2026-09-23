from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import UpdateView

from app.oferta_praca.forms import OfferCreateForm
from app.oferta_praca.models import Offer, OfferImage, OfferActivity
from app.dokument.models import DocumentFolder


class OfferUpdateView(LoginRequiredMixin, UpdateView):
    model = Offer
    form_class = OfferCreateForm
    template_name = "app/oferta_praca/offer_form.html"
    context_object_name = "offer"

    def get_queryset(self):
        return Offer.objects.filter(company=self.request.user.company)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.user.company
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        offer = form.save(commit=False)
        offer.company = self.request.user.company
        offer.save()

        form.save_m2m()

        images = self.request.FILES.getlist("images")
        for image in images:
            OfferImage.objects.create(
                company=self.request.user.company,
                offer=offer,
                file=image,
            )

        OfferActivity.objects.create(
            company=offer.company,
            offer=offer,
            type=OfferActivity.Type.SYSTEM,
            title="Edytowano ofertę",
            description=f"Zaktualizowano dane oferty {offer.number}",
            created_by=self.request.user,
        )

        messages.success(self.request, "Oferta została zaktualizowana.")
        return redirect("offer_detail", pk=offer.pk)

    def get_success_url(self):
        return reverse("offer_detail", kwargs={"pk": self.object.pk})