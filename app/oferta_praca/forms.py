# app/offers/forms.py
from django import forms
from django.forms.widgets import ClearableFileInput

from app.klient.models import ClientLocation
from app.oferta_praca.models import Offer, OfferVariant, OfferVariantItem
from app.magazyn.models import Product
from django.forms.models import inlineformset_factory



class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class OfferCreateForm(forms.ModelForm):
    images = forms.ImageField(
        required=False,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
                "multiple": True,
            }
        ),
        label="Zdjęcia",
    )

    class Meta:
        model = Offer
        fields = ["title", "client", "location", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "client": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields["client"].queryset = self.fields["client"].queryset.filter(company=company)

        self.fields["location"].queryset = ClientLocation.objects.none()
        self.fields["location"].required = False

        client_id = self.data.get("client") or getattr(self.instance, "client_id", None)
        if client_id:
            self.fields["location"].queryset = ClientLocation.objects.filter(client_id=client_id)


class ProductSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )

        if value:
            product = self.product_map.get(str(value))
            if product:
                option["attrs"]["data-product-type"] = getattr(product, "type", "") or ""
                option["attrs"]["data-product-name"] = getattr(product, "name", "") or ""
                option["attrs"]["data-product-unit"] = getattr(product, "unit", "") or ""
                option["attrs"]["data-product-price"] = str(getattr(product, "net_price", "") or "")
                option["attrs"]["data-product-vat"] = str(getattr(product, "vat_rate", "") or "")

        return option


class OfferVariantCreateForm(forms.ModelForm):
    pdf_file = forms.FileField(
        required=False,
        label="Plik PDF",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".pdf,application/pdf",
            }
        ),
    )

    pdf_total_netto = forms.DecimalField(
        required=False,
        label="Cena oferty netto",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    pdf_accessories_netto = forms.DecimalField(
        required=False,
        label="Cena akcesoriów netto",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    pdf_materials_netto = forms.DecimalField(
        required=False,
        label="Cena materiałów netto",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    class Meta:
        model = OfferVariant
        fields = [
            "source_type",
            "name",
            "description",
            "is_selected",
        ]
        widgets = {
            "source_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_selected": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "source_type": "Sposób utworzenia",
            "name": "Nazwa wariantu",
            "description": "Opis",
            "is_selected": "Wybrany wariant",
        }

    def __init__(self, *args, **kwargs):
        self.offer = kwargs.pop("offer", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            return name

        offer = self.offer
        if not offer and self.instance and self.instance.pk:
            offer = self.instance.offer

        if offer:
            qs = OfferVariant.objects.filter(offer=offer, name=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError("Wariant o takiej nazwie już istnieje w tej ofercie.")

        return name

    def clean(self):
        cleaned = super().clean()
        source_type = cleaned.get("source_type")
        pdf_file = cleaned.get("pdf_file")

        if source_type == OfferVariant.SourceType.PDF:
            if not pdf_file and not (self.instance and self.instance.pk and self.instance.files.exists()):
                self.add_error("pdf_file", "Dodaj plik PDF.")
            if cleaned.get("pdf_total_netto") in (None, ""):
                self.add_error("pdf_total_netto", "Podaj cenę oferty netto.")

        if source_type == OfferVariant.SourceType.PDF and pdf_file and not cleaned.get("name"):
            cleaned["name"] = os.path.splitext(pdf_file.name)[0]

        return cleaned


class OfferVariantItemForm(forms.ModelForm):
    item_type = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = OfferVariantItem
        fields = [
            "item_type",
            "product",
            "name",
            "quantity",
            "unit",
            "unit_price_netto",
            "vat_rate",
        ]
        widgets = {
            "product": ProductSelect(attrs={"class": "form-select product-select"}),
            "name": forms.TextInput(attrs={"class": "form-control item-name-input"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit": forms.TextInput(attrs={"class": "form-control item-unit-input"}),
            "unit_price_netto": forms.NumberInput(attrs={"class": "form-control item-price-input", "step": "0.01"}),
            "vat_rate": forms.NumberInput(attrs={"class": "form-control item-vat-input", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        products = Product.objects.none()
        if company:
            products = Product.objects.filter(
                company=company,
                is_active=True
            ).order_by("name")

        self.fields["product"].queryset = products

        widget = self.fields["product"].widget
        if isinstance(widget, ProductSelect):
            widget.product_map = {str(p.pk): p for p in products}

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")

        is_empty_row = not any([
            cleaned.get("product"),
            cleaned.get("name"),
            cleaned.get("quantity"),
            cleaned.get("unit"),
            cleaned.get("unit_price_netto"),
            cleaned.get("vat_rate"),
        ])
        if is_empty_row:
            return cleaned

        if not product:
            self.add_error("product", "Wybierz produkt.")
            return cleaned

        cleaned["item_type"] = product.type

        if not cleaned.get("name"):
            cleaned["name"] = product.name

        if not cleaned.get("unit"):
            cleaned["unit"] = product.unit

        if cleaned.get("unit_price_netto") in (None, ""):
            cleaned["unit_price_netto"] = product.net_price

        if cleaned.get("vat_rate") in (None, ""):
            cleaned["vat_rate"] = product.vat_rate

        return cleaned

OfferVariantItemFormSet = inlineformset_factory(
    OfferVariant,
    OfferVariantItem,
    form=OfferVariantItemForm,
    extra=3,
    can_delete=True,
)