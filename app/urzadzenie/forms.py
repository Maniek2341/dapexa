from django import forms
from app.urzadzenie.models import Product, ProductCategory


class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "type",
            "category",
            "unit",
            "net_price",
            "vat_rate",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Kamera IP Hikvision",
            }),
            "sku": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. CAM-HIK-001",
            }),
            "type": forms.Select(attrs={
                "class": "form-select",
            }),
            "category": forms.Select(attrs={
                "class": "form-select",
            }),
            "unit": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "szt.",
            }),
            "net_price": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
            "vat_rate": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

        labels = {
            "name": "Nazwa",
            "sku": "SKU / Kod",
            "type": "Typ pozycji",
            "category": "Kategoria",
            "unit": "Jednostka",
            "net_price": "Cena netto",
            "vat_rate": "VAT %",
            "is_active": "Aktywna pozycja",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user and hasattr(self.user, "company"):
            self.fields["category"].queryset = ProductCategory.objects.filter(
                company=self.user.company
            ).order_by("name")
        else:
            self.fields["category"].queryset = ProductCategory.objects.none()