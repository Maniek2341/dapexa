from django import forms
from app.gwarancja.models import *



class MultipleFileInput(forms.ClearableFileInput):

    allow_multiple_selected = True

class MultipleFileField(forms.FileField):

    def __init__(self, *args, **kwargs):

        kwargs.setdefault("widget", MultipleFileInput())

        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):

        if not data:

            return []

        if isinstance(data, (list, tuple)):

            return [super(MultipleFileField, self).clean(d, initial) for d in data]

        return [super().clean(data, initial)]

class WarrantyClaimForm(forms.ModelForm):
    files = MultipleFileField(
        required=False,
        label="Zdjęcia",
        widget=MultipleFileInput(attrs={
            "class": "form-control",
            "accept": "image/*",
            "multiple": True,
        })
    )

    class Meta:
        model = WarrantyClaim
        fields = [
            "provider",
            "client",
            "location",
            "product",
            "fault_description",
            "notes",
        ]

        widgets = {
            "provider": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "...",
            }),
            "client": forms.Select(attrs={
                "class": "form-select",
            }),
            "location": forms.Select(attrs={
                "class": "form-select",
            }),
            "product": forms.Select(attrs={
                "class": "form-select",
            }),
            "fault_description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Opisz usterkę...",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Dodatkowe notatki...",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user and hasattr(self.user, "company"):
            company = self.user.company

            self.fields["client"].queryset = self.fields["client"].queryset.filter(
                company=company
            )

            self.fields["location"].queryset = self.fields["location"].queryset.filter(
                company=company
            )

            self.fields["product"].queryset = self.fields["product"].queryset.filter(
                company=company
            )

        self.fields["location"].required = False
        self.fields["product"].required = False
        self.fields["provider"].required = False
        self.fields["notes"].required = False