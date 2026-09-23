from django import forms
from django.core.exceptions import ValidationError

from app.magazyn.models import StockItem, Warehouse
from app.urzadzenie.models import Product


class WarehouseCreateForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ["name", "description", "is_default"]
        labels = {"name": "Nazwa magazynu", "description": "Opis", "is_default": "Ustaw jako domyślny"}
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "np. Magazyn główny"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class StockItemCreateForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = [
            "warehouse",
            "product",
            "quantity",
            "min_quantity",
        ]

        widgets = {
            "warehouse": forms.Select(attrs={"class": "form-select"}),
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
            "min_quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
        }

        labels = {
            "warehouse": "Magazyn",
            "product": "Produkt",
            "quantity": "Ilość na stanie",
            "min_quantity": "Minimalny stan",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user and self.user.company:
            self.fields["warehouse"].queryset = Warehouse.objects.filter(
                company=self.user.company
            ).order_by("name")

            self.fields["product"].queryset = Product.objects.filter(
                company=self.user.company,
                is_active=True,
            ).order_by("name")
        else:
            self.fields["warehouse"].queryset = Warehouse.objects.none()
            self.fields["product"].queryset = Product.objects.none()

    def clean(self):
        cleaned_data = super().clean()

        warehouse = cleaned_data.get("warehouse")
        product = cleaned_data.get("product")

        if self.user and warehouse and product:
            exists = StockItem.objects.filter(
                company=self.user.company,
                warehouse=warehouse,
                product=product,
            ).exists()

            if exists:
                raise ValidationError(
                    "Ten produkt jest już dodany do wybranego magazynu."
                )

        return cleaned_data

class StockMovementForm(forms.Form):
    quantity = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "0.01",
        }),
        label="Ilość",
    )

    document_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
        }),
        label="Numer dokumentu",
    )

    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
        }),
        label="Notatka",
    )
