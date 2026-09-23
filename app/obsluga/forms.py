# app/obsluga/forms.py

from django import forms
from django.forms.widgets import ClearableFileInput

from app.obsluga.models import ServiceContract, ServiceContractAsset, ServiceContractParameter, ServiceContractMedia
from app.klient.models import Client, ClientLocation
from app.core.models import PanelUser


class MultipleFileInput(ClearableFileInput):

    allow_multiple_selected = True

class MultipleFileField(forms.FileField):

    def clean(self, data, initial=None):
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [
                super(MultipleFileField, self).clean(file, initial)
                for file in data
            ]
        return [super().clean(data, initial)]

class ServiceContractForm(forms.ModelForm):
    images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            "class": "form-control",
            "multiple": True,
            "accept": "image/*",
        }),
        label="Zdjęcia",
    )

    attachments = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            "class": "form-control",
            "multiple": True,
        }),
        label="Załączniki",
    )
    class Meta:
        model = ServiceContract
        fields = [
            "client",
            "location",
            "title",
            "contract_type",
            "status",
            "frequency",
            "start_date",
            "end_date",
            "next_service_date",
            "caretaker",
            "description",
            "notes",
            "monthly_price_net",
        ]

        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Obsługa monitoringu - Wspólnota X",
            }),
            "contract_type": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "frequency": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "next_service_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "caretaker": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Opisz zakres obsługi...",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Uwagi wewnętrzne...",
            }),
            "monthly_price_net": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
        }

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        self.fields["location"].required = False

        self.fields["end_date"].required = False

        self.fields["next_service_date"].required = False

        self.fields["caretaker"].required = False

        self.fields["description"].required = False

        self.fields["notes"].required = False

        if not self.user:

            return

        company = self.user.company

        self.fields["client"].queryset = Client.objects.filter(

            company=company

        )

        self.fields["caretaker"].queryset = PanelUser.objects.filter(

            company=company,

            is_active=True,

        )

        self.fields["location"].queryset = ClientLocation.objects.none()

        client_id = None

        if self.data.get("client"):

            client_id = self.data.get("client")

        elif self.instance and self.instance.pk:

            client_id = self.instance.client_id

        if client_id:

            self.fields["location"].queryset = ClientLocation.objects.filter(

                client_id=client_id,

                client__company=company,

            )


class ServiceContractAssetForm(forms.ModelForm):

    class Meta:

        model = ServiceContractAsset

        fields = [
            "name",
            "asset_type",
            "location_description",
            "producer",
            "model",
            "serial_number",
            "ip_address",
            "notes",
        ]

        widgets = {

            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Rejestrator Hikvision, Rozdzielnia RG",
            }),

            "asset_type": forms.Select(attrs={
                "class": "form-select",
            }),

            "location_description": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. strych klatka 15, serwerownia, parter",
            }),

            "producer": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Hikvision, Eaton, LG",
            }),

            "model": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Model",
            }),

            "serial_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Numer seryjny",
            }),

            "ip_address": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. 192.168.1.100",
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Uwagi do elementu",
            }),

        }


class ServiceContractParameterForm(forms.ModelForm):
    class Meta:
        model = ServiceContractParameter
        fields = [
            "name",
            "value",
            "unit",
            "group",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Dni nagrań, Ilość kamer, Moc",
            }),
            "value": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. 32, 7, SmartPSS",
            }),
            "unit": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. dni, szt., kW",
            }),
            "group": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. CCTV, Elektryka, Klimatyzacja",
            }),
        }


class ServiceContractMediaForm(forms.ModelForm):
    class Meta:
        model = ServiceContractMedia
        fields = ["file", "title", "media_type"]

        widgets = {
            "file": forms.ClearableFileInput(attrs={
                "class": "form-control",
            }),
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. zdjęcie rejestratora, umowa PDF",
            }),
            "media_type": forms.Select(attrs={
                "class": "form-select",
            }),
        }