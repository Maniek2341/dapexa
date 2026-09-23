import os
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import UpdateView

from app.oferta_praca.forms import OfferVariantCreateForm, OfferVariantItemFormSet
from app.oferta_praca.models import OfferVariant, OfferVariantFile, OfferActivity
from app.dokument.models import DocumentFolder


class OfferVariantUpdateView(LoginRequiredMixin, UpdateView):
    model = OfferVariant
    form_class = OfferVariantCreateForm
    template_name = "app/oferta_praca/offer_variant_form.html"
    context_object_name = "variant"

    def get_queryset(self):
        return OfferVariant.objects.select_related("offer").filter(
            company=self.request.user.company
        )

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.offer = self.object.offer
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        variant = self.object

        if variant.source_type == OfferVariant.SourceType.PDF:
            initial["pdf_total_netto"] = variant.total_netto
            initial["pdf_accessories_netto"] = variant.accessories_netto
            initial["pdf_materials_netto"] = variant.materials_netto
            initial["pdf_labor_netto"] = variant.labor_netto

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["item_formset"] = OfferVariantItemFormSet(
                self.request.POST,
                instance=self.object,
                prefix="items",
                form_kwargs={"company": self.request.user.company},
            )
        else:
            context["item_formset"] = OfferVariantItemFormSet(
                instance=self.object,
                prefix="items",
                form_kwargs={"company": self.request.user.company},
            )

        context["offer"] = self.offer
        context["is_edit"] = True
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

        variant.save()

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
            labor = form.cleaned_data.get("pdf_labor_netto") or Decimal("0")

            variant.total_netto = total_netto
            variant.accessories_netto = accessories
            variant.materials_netto = materials
            variant.labor_netto = labor
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

                if item.product and not item.name:
                    item.name = str(item.product)

                if item.product:
                    if hasattr(item.product, "unit") and not item.unit:
                        item.unit = item.product.unit or "szt."
                    if hasattr(item.product, "net_price") and not item.unit_price_netto:
                        item.unit_price_netto = item.product.net_price or Decimal("0")
                    if hasattr(item.product, "vat_rate") and not item.vat_rate:
                        item.vat_rate = item.product.vat_rate or Decimal("23")

                item.save()

            for obj in item_formset.deleted_objects:
                obj.delete()

            variant.recalculate_totals()
        OfferActivity.objects.create(
            company=self.offer.company,
            offer=self.offer,
            type=OfferActivity.Type.VARIANT,
            title="Edytowano wariant",
            description=f"Edytowano wariant: {variant.name} | wartość: {variant.total_netto} zł",
            created_by=self.request.user,
        )

        messages.success(self.request, "Wariant został zaktualizowany.")
        return redirect("offer_detail", pk=self.offer.pk)

    def form_invalid(self, form):
        messages.error(self.request, "Popraw błędy w formularzu.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("offer_detail", kwargs={"pk": self.offer.pk})