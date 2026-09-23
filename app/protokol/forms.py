from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError

from app.core.models import PanelUser
from app.urzadzenie.models import Product
from .models import Protocol, ProtokolImage, ProtokolUrzadzenia
from app.klient.models import Client, ClientLocation
from django.urls import reverse_lazy


class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = forms.FileField.clean

        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return [single_file_clean(self, d, initial) for d in data]

        return [single_file_clean(self, data, initial)]



class ProtocolCreateForm(forms.ModelForm):

    attachments = MultipleFileField(
        required=False,
        label="Zdjęcia / załączniki",
        widget=MultipleFileInput(attrs={"multiple": True, "class": "form-control",})
    )

    class Meta:
        model = Protocol
        fields = [
            "client",
            "title",
            "end_time",
            "wykonane_prace",
            "robocizna",
            "pracownicy_szt",
            "dojazdy_szt",
            "rodzaj_prac",
            "dodatkowe_materialy",
            "location",
        ]

        labels = {
            "client": "Klient",
            "title": "Tytuł protokołu",
            "end_time": "Data zakończenia",
            "wykonane_prace": "Wykonane prace",
            "robocizna": "Czas pracy (h)",
            "pracownicy_szt": "Ilość pracowników",
            "dojazdy_szt": "Ilość dojazdów",
            "rodzaj_prac": "Rodzaj prac",
            "dodatkowe_materialy": "Dodatkowe urządzenia/materiały"
        }

        widgets = {
            "end_time": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control"
            }),
            "wykonane_prace": forms.Textarea(attrs={
                "rows": 4,
                "class": "form-control"
            }),
            "dodatkowe_materialy": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "maxlength": 250,
                "placeholder": "Np. silikon, wkręty, drobne elementy..."
            }),
            "end_time": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                },
            ),
        }
        

    # ------------------------------------------------

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["client"].queryset = Client.objects.filter(
            company=self.user.company,
            is_active=True
        )

        if not self.instance.pk:
            now_local = timezone.localtime(timezone.now())
            self.initial["end_time"] = now_local.strftime("%Y-%m-%dT%H:%M")

        ## 🔥 przy edycji — przelicz na localtime
        if self.instance.pk and self.instance.end_time:
            self.initial["end_time"] = timezone.localtime(
                self.instance.end_time
            ).strftime("%Y-%m-%dT%H:%M")

        for name, field in self.fields.items():
            if name == "attachments":
                continue

            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-select"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control"})
            elif not isinstance(field.widget, forms.DateTimeInput):
                field.widget.attrs.update({"class": "form-control"})

        # 🔒 jeśli edycja (instance istnieje)
        if self.instance and self.instance.pk:
            # 🔒 klient readonly
            self.fields["client"].disabled = True

            # ✅ lokalizacje tylko tego klienta
            self.fields["location"].queryset = (
                ClientLocation.objects.filter(
                    client=self.instance.client,
                    is_active=True
                )
            )

        # ✅ ustaw queryset lokalizacji tak, żeby zawierał WYBRANĄ lokalizację
        if "location" in self.fields:
            # domyślnie nic
            self.fields["location"].queryset = ClientLocation.objects.none()

            client = None
            if self.instance and self.instance.pk:
                client = self.instance.client
            else:
                # create: klient z POST/initial
                client_id = self.data.get("client") or self.initial.get("client")
                if client_id:
                    try:
                        client = Client.objects.get(pk=client_id, company=user.company)
                    except Client.DoesNotExist:
                        client = None

            if client:
                if client.client_type == "firma":
                    self.fields["location"].widget.attrs.pop("disabled", None)
                else:
                    # 👇 ukryj pole dla osoby prywatnej
                    self.fields["location"].widget = forms.HiddenInput()

        # podstawowe klasy
        for name, field in self.fields.items():
            if getattr(field.widget, "attrs", None) is not None:
                field.widget.attrs.setdefault("class", "form-control")

        # selecty
        for name in ("client", "priority", "location"):
            if name in self.fields:
                self.fields[name].widget.attrs["class"] = "form-select"

        if user and getattr(user, "company_id", None):

            # klient tylko z firmy
            self.fields["client"].queryset = Client.objects.filter(
                company=user.company,
                is_active=True
            )


            # 🔥 LOKALIZACJE – dynamicznie po kliencie
            self.fields["location"].queryset = ClientLocation.objects.none()

            # przy edycji
            if self.instance.pk and self.instance.client:
                self.fields["location"].queryset = ClientLocation.objects.filter(
                    company=user.company,
                    client=self.instance.client,
                    is_active=True
                )

            # przy POST (gdy zmieniono klienta)
            if "client" in self.data:
                try:
                    client_id = int(self.data.get("client"))
                    self.fields["location"].queryset = ClientLocation.objects.filter(
                        company=user.company,
                        client_id=client_id,
                        is_active=True
                    )
                except (ValueError, TypeError):
                    pass

    # ------------------------------------------------
    # WALIDACJA BIZNESOWA
    # ------------------------------------------------

    def clean(self):
        cleaned_data = super().clean()

        robocizna = cleaned_data.get("robocizna")
        pracownicy = cleaned_data.get("pracownicy_szt")
        dojazdy = cleaned_data.get("dojazdy_szt")

        if robocizna is not None and robocizna < 0:
            raise ValidationError("Czas pracy nie może być ujemny.")

        if pracownicy and pracownicy < 1:
            raise ValidationError("Musi być co najmniej 1 pracownik.")

        if dojazdy is not None and dojazdy < 0:
            raise ValidationError("Ilość dojazdów nie może być ujemna.")

        client = cleaned_data.get("client")
        location = cleaned_data.get("location")

        if client and client.client_type == "firma" and not location:
            self.add_error("location", "Wybierz lokalizację dla firmy.")

        return cleaned_data

    # ------------------------------------------------
    # WALIDACJA PLIKÓW
    # ------------------------------------------------

    def clean_attachments(self):
        files = self.files.getlist("attachments")

        for file in files:
            if file.size > 5 * 1024 * 1024:
                raise ValidationError(
                    f"Plik {file.name} przekracza 5MB."
                )

            allowed_types = [
                "image/jpeg",
                "image/png",
                "image/webp",
                "application/pdf"
            ]

            if file.content_type not in allowed_types:
                raise ValidationError(
                    f"Niedozwolony typ pliku: {file.name}"
                )

        return files


    # ------------------------------------------------
    # SAVE
    # ------------------------------------------------

    def save(self, commit=True):
        instance: Protocol = super().save(commit=False)

        # 🔒 Firma + pracownik
        if self.user and getattr(self.user, "company", None):
            if not getattr(instance, "company_id", None):
                instance.company = self.user.company

        instance.pracownik = self.user

        # ============================================
        # 🔥 SNAPSHOT ADRESU
        # ============================================

        # ============================================
        # 🔥 SNAPSHOT ADRESU (WERSJA BEZPIECZNA)
        # ============================================

        addr = None

        client = None
        location = None

        if getattr(instance, "location_id", None):
            location = instance.location

        if getattr(instance, "client_id", None):
            client = instance.client

        if location and getattr(location, "address", None):
            addr = location.address

        elif client and getattr(client, "shipping_address", None):
            addr = client.shipping_address

        elif client and getattr(client, "billing_address", None):
            addr = client.billing_address

        if addr:
            instance.address_street = getattr(addr, "street", "")
            instance.address_city = getattr(addr, "city", "")
            instance.address_postal_code = getattr(addr, "postcode", "")
            instance.address_country = getattr(addr, "country", "")
            instance.address_latitude = getattr(addr, "latitude", None)
            instance.address_longitude = getattr(addr, "longitude", None)
        else:
            instance.address_street = ""
            instance.address_city = ""
            instance.address_postal_code = ""
            instance.address_country = ""
            instance.address_latitude = None
            instance.address_longitude = None

        # ============================================
        # 📅 Data
        # ============================================

        if not instance.end_time:
            instance.end_time = timezone.now()

        # ============================================
        # 🔢 Numer
        # ============================================

        if not instance.number:
            year = instance.end_time.year
            instance.number = Protocol.generate_number(self.user.company, year)

        # ============================================
        # 💾 SAVE
        # ============================================

        if commit:
            instance.save()
            self.save_m2m()

            # 📎 Załączniki
            files = self.cleaned_data.get("attachments", [])
            for file in files:
                ProtokolImage.objects.create(
                    protokol=instance,
                    file=file,
                    kind="image" if file.content_type.startswith("image") else "file",
                    original_name=file.name,
                    uploaded_by=self.user
                )

        return instance

class ProtokolUrzadzeniaForm(forms.ModelForm):

    class Meta:
        model = ProtokolUrzadzenia
        fields = ["urzadzenia", "sztuki"]

        labels = {
            "urzadzenia": "Produkt",
            "sztuki": "Ilość",
        }

        widgets = {
            "urzadzenia": forms.Select(attrs={
                "class": "form-select ajax-select",
                "data-url": reverse_lazy("ajax_products"),
                "data-placeholder": "Wyszukaj produkt...",
            }),
            "sztuki": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "placeholder": "Ilość",
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        self.fields["urzadzenia"].queryset = Product.objects.filter(
            company=user.company,
            is_active=True
        )   

    def clean_sztuki(self):
        qty = self.cleaned_data.get("sztuki")
        if qty and qty <= 0:
            raise forms.ValidationError("Ilość musi być większa od 0.")
        return qty

ProtokolUrzadzeniaFormSet = forms.inlineformset_factory(
    Protocol,
    ProtokolUrzadzenia,
    form=ProtokolUrzadzeniaForm,
    extra=1,
    can_delete=True
)
