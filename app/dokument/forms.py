from django import forms

from app.dokument.models import Document


class DocumentCreateForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            "name",
            "file",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nazwa dokumentu",
            }),

            "file": forms.FileInput(attrs={
                "class": "form-control",
            }),
        }