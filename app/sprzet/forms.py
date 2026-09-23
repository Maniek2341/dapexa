# app/sprzet/forms.py

from django import forms
from app.sprzet.models import Tool, ToolEvent


class ToolCreateForm(forms.ModelForm):
    class Meta:
        model = Tool
        fields = [
            "image",
            "name",
            "category",
            "status",
            "manufacturer",
            "model",
            "serial_number",
            "inventory_number",
            "purchase_date",
            "warranty_until",
            "purchase_price_net",
            "current_holder",
            "storage_place",
            "last_inspection_date",
            "next_inspection_date",
        ]

        widgets = {
            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Wiertarka udarowa Bosch",
            }),
            "category": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "manufacturer": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Bosch, Makita, DeWalt",
            }),
            "model": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Model sprzętu",
            }),
            "serial_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Numer seryjny",
            }),
            "inventory_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Numer ewidencyjny",
            }),
            "purchase_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "warranty_until": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "purchase_price_net": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
            }),
            "current_holder": forms.Select(attrs={"class": "form-select"}),
            "storage_place": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Magazyn, auto serwisowe, biuro",
            }),
            "last_inspection_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "next_inspection_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            self.fields["current_holder"].queryset = (
                user.__class__.objects
                .filter(company=user.company)
                .order_by("first_name", "last_name", "email")
            )

        self.fields["current_holder"].required = False
        self.fields["current_holder"].empty_label = "Brak przypisanego pracownika"


class ToolEventForm(forms.ModelForm):
    images = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/*",
        }),
        label="Zdjęcia",
    )

    class Meta:
        model = ToolEvent
        fields = [
            "type",
            "description",
            "event_date",
        ]

        widgets = {
            "type": forms.Select(attrs={
                "class": "form-select",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Opisz zdarzenie...",
            }),
            "event_date": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }),
        }