# app/vehicles/forms.py
from django import forms
from app.pojazd.models import Vehicle, VehicleEvent


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "registration_number",
            "brand",
            "model",
            "vin",
            "current_mileage",
            "insurance_valid_until",
            "inspection_valid_until",
            "photo",
            "is_active",
        ]

        widgets = {
            "registration_number": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "model": forms.TextInput(attrs={"class": "form-control"}),
            "vin": forms.TextInput(attrs={"class": "form-control"}),
            "current_mileage": forms.NumberInput(attrs={"class": "form-control"}),
            "insurance_valid_until": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "inspection_valid_until": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class VehicleEventForm(forms.ModelForm):
    class Meta:
        model = VehicleEvent
        fields = [
            "event_type",
            "description",
            "event_date",
            "mileage",
            "photo",
        ]

        widgets = {
            "event_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
            }),
            "event_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "mileage": forms.NumberInput(attrs={"class": "form-control"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }