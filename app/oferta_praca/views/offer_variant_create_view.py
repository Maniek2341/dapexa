import os
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView

from app.oferta_praca.forms import OfferVariantCreateForm, OfferVariantItemFormSet
from app.oferta_praca.models import Offer, OfferVariant, OfferVariantFile, OfferActivity
from app.dokument.models import DocumentFolder


class OfferVariantCreateView(LoginRequiredMixin, CreateView):
    model = OfferVariant
    form_class = OfferVariantCreateForm
    template_name = "app/oferta_praca/offer_variant_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.offer = get_object_or_404(
            Offer,
            pk=self.kwargs["offer_pk"],
            company=request.user.company,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["offer"] = self.offer
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["item_formset"] = OfferVariantItemFormSet(
                self.request.POST,
                prefix="items",
                form_kwargs={"company": self.request.user.company},
            )
        else:
            context["item_formset"] = OfferVariantItemFormSet(
                prefix="items",
                form_kwargs={"company": self.request.user.company},
            )

        context["offer"] = self.offer
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context["item_formset"]

        source_type = form.cleaned_data["source_type"]

        if source_type == OfferVariant.SourceType.ITEMS and not item_formset.is_valid():
            return self.form_invalid(form)

        variant = form.save(commit=False)
        variant.offer = self.offer
        variant.company = self.offer.company
        variant.source_type = source_type

        if variant.is_selected and not variant.selected_at:
            variant.selected_at = timezone.now()

        pdf_file = form.cleaned_data.get("pdf_file")

        if source_type == OfferVariant.SourceType.PDF and pdf_file and not variant.name:
            variant.name = os.path.splitext(pdf_file.name)[0]

        try:
            with transaction.atomic():
                variant.save()
        except IntegrityError:
            form.add_error("name", "Wariant o takiej nazwie już istnieje w tej ofercie.")
            return self.form_invalid(form)

        if source_type == OfferVariant.SourceType.PDF:
            if pdf_file:
                OfferVariantFile.objects.create(
                    company=self.offer.company,
                    variant=variant,
                    file=pdf_file,
                    title=os.path.splitext(pdf_file.name)[0],
                )

            total_netto = form.cleaned_data.get("pdf_total_netto") or Decimal("0")
            accessories = form.cleaned_data.get("pdf_accessories_netto") or Decimal("0")
            materials = form.cleaned_data.get("pdf_materials_netto") or Decimal("0")

            variant.total_netto = total_netto
            variant.accessories_netto = accessories
            variant.materials_netto = materials
            variant.labor_netto = Decimal("0")
            variant.services_netto = Decimal("0")
            variant.other_netto = Decimal("0")
            variant.total_vat = Decimal("0")
            variant.total_brutto = total_netto

            variant.save(update_fields=[
                "source_type",
                "materials_netto",
                "accessories_netto",
                "labor_netto",
                "services_netto",
                "other_netto",
                "total_netto",
                "total_vat",
                "total_brutto",
            ])

        else:
            item_formset.instance = variant
            items = item_formset.save(commit=False)

            for item in items:
                item.company = self.offer.company

                if item.product:
                    item.item_type = item.product.type

                    if not item.name:
                        item.name = item.product.name
                    if not item.unit:
                        item.unit = item.product.unit or "szt."
                    if item.unit_price_netto in (None, ""):
                        item.unit_price_netto = item.product.net_price or Decimal("0")
                    if item.vat_rate in (None, ""):
                        item.vat_rate = item.product.vat_rate or Decimal("23")

                item.save()

            for obj in item_formset.deleted_objects:
                obj.delete()

            variant.recalculate_totals()
    
        OfferActivity.objects.create(
            company=self.offer.company,
            offer=self.offer,
            type=OfferActivity.Type.VARIANT,
            title="Dodano wariant",
            description=f"Dodano wariant: {variant.name}",
            created_by=self.request.user,
        )
        
        self.object = variant
        messages.success(self.request, "Wariant został dodany.")
        return redirect("offer_detail", pk=self.offer.pk)

    