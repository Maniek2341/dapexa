# app/services/forms.py
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from app.core.models import PanelUser
from app.klient.models import Client, ClientLocation
from app.serwis.models import ServiceNote, ServiceOrder, ServiceOrderMedia, ServiceWorkLog



class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            # UWAGA: nie używamy super() bez args w list comprehension
            return [forms.FileField.clean(self, d, initial) for d in data]
        return [forms.FileField.clean(self, data, initial)]

User = get_user_model()

MAX_ASSIGNED = 3

MAX_IMAGE_MB = 8
MAX_FILE_MB = 25

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class ServiceOrderCreateForm(forms.ModelForm):
    """
    Formularz dodawania zgłoszenia serwisowego (ServiceOrder) z walidacją:
    - client tylko z firmy użytkownika i aktywny
    - assigned_to max 3 osoby i tylko z firmy użytkownika (opcjonalnie: aktywni)
    - planned_end >= planned_start
    - wybór rodzaju zgłoszenia: serwis albo obsługa
    - opcjonalnie: upload zdjęć i załączników (multi) do ServiceOrderMedia
    """

    TYPE_SERVICE = "service"
    TYPE_MAINTENANCE = "maintenance"
    TYPE_CHOICES = (
        (TYPE_SERVICE, "Serwis"),
        (TYPE_MAINTENANCE, "Obsługa"),
    )

    service_type = forms.ChoiceField(
        label="Rodzaj zgłoszenia",
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    settlement_method = forms.ChoiceField(
        label="Sposób rozliczenia",
        choices=ServiceOrder.SettlementMethod.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # --- MEDIA (opcjonalnie) ---
    images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True}),
        label="Pliki (zdjęcia i załączniki)",
    )
    attachments = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True}),
        label="Załączniki",
    )

    class Meta:
        model = ServiceOrder
        fields = [
            "title",
            "client",
            "location",   # 👈 DODAJ
            "description",
            "priority",
            "settlement_method",
            "planned_start",
            "planned_end",
            "assigned_to",
        ]
        widgets = {
            "planned_start": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "class": "form-control schedule-input",
                    "autocomplete": "off",
                },
            ),
            "planned_end": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "class": "form-control schedule-input",
                    "autocomplete": "off",
                },
            ),
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["planned_start"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["planned_end"].input_formats = ["%Y-%m-%dT%H:%M"]

        if self.instance and self.instance.pk:
            self.fields["service_type"].initial = (
                self.TYPE_MAINTENANCE
                if self.instance.status == ServiceOrder.Status.OBSLUGA
                else self.TYPE_SERVICE
            )
            self.fields["service_type"].disabled = True
        else:
            self.fields["service_type"].initial = self.TYPE_SERVICE

            # Nowe zgłoszenie nie otrzymuje automatycznego terminu.
            # Dane z nieudanego POST pozostają bez zmian, aby użytkownik ich nie utracił.
            if not self.is_bound:
                self.initial.pop("planned_start", None)
                self.initial.pop("planned_end", None)
                self.fields["planned_start"].initial = None
                self.fields["planned_end"].initial = None
                for field_name in ("planned_start", "planned_end"):
                    self.fields[field_name].widget.attrs.update({
                        "autocomplete": "new-password",
                        "readonly": True,
                        "data-empty-on-create": "true",
                    })

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
                qs = ClientLocation.objects.filter(company=user.company, client=client, is_active=True)

                # 🔥 ważne: jeśli już jest wybrana lokalizacja na obiekcie, upewnij się, że jest w queryset
                if self.instance and self.instance.location_id:
                    qs = qs | ClientLocation.objects.filter(pk=self.instance.location_id)

                self.fields["location"].queryset = qs.distinct()

                # ✅ to sprawi, że w select będzie zaznaczona aktualna lokalizacja (dla edit)
                if self.instance and self.instance.location_id:
                    self.initial["location"] = self.instance.location_id

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

            # pracownicy
            qs = PanelUser.objects.filter(company=user.company)
            if hasattr(PanelUser, "is_active"):
                qs = qs.filter(is_active=True)
            self.fields["assigned_to"].queryset = qs

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

    # ---------- WALIDACJE ----------

    def clean_location(self):
        location = self.cleaned_data.get("location")
        client = self.cleaned_data.get("client")

        if client:
            locations_count = client.locations.filter(is_active=True).count()

            if locations_count > 1 and not location:
                raise ValidationError("Wybierz lokalizację dla tego klienta.")

        return location

    def clean_assigned_to(self):
        workers = self.cleaned_data.get("assigned_to")
        if workers and workers.count() > MAX_ASSIGNED:
            raise ValidationError(f"Możesz przypisać maksymalnie {MAX_ASSIGNED} osoby do serwisu.")
        return workers

    def clean(self):
        cleaned = super().clean()

        start = cleaned.get("planned_start")
        end = cleaned.get("planned_end")
        if start and end and end < start:
            self.add_error("planned_end", "Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.")

        return cleaned

    # ---------- MEDIA (opcjonalnie) ----------

    def clean_images(self):
        files = self.files.getlist("images")
        if not files:
            return files

        for f in files:
            if getattr(f, "content_type", None) not in ALLOWED_IMAGE_TYPES:
                raise ValidationError(f"Nieprawidłowy typ zdjęcia: {f.name}")
            if f.size > MAX_IMAGE_MB * 1024 * 1024:
                raise ValidationError(f"Zdjęcie za duże (max {MAX_IMAGE_MB}MB): {f.name}")
        return files

    def clean_attachments(self):
        files = self.files.getlist("attachments")
        if not files:
            return files

        for f in files:
            if f.size > MAX_FILE_MB * 1024 * 1024:
                raise ValidationError(f"Plik za duży (max {MAX_FILE_MB}MB): {f.name}")
        return files

    def save(self, commit=True):
        obj: ServiceOrder = super().save(commit=False)

        if not obj.pk:
            if self.cleaned_data.get("service_type") == self.TYPE_MAINTENANCE:
                obj.status = ServiceOrder.Status.OBSLUGA
                obj.status_zgrania = ServiceOrder.StatusZgrania.ZGRANIE_NEW
            else:
                obj.status = ServiceOrder.Status.NEW

        # 🔒 przypisz firmę jeśli nowy
        if self.user and getattr(self.user, "company", None) and not getattr(obj, "company_id", None):
            obj.company = self.user.company

        # 🔥 LOGIKA ADRESU SERWISU
        if obj.location and obj.location.address:
            obj.address = obj.location.address
        else:
            if obj.client and obj.client.shipping_address:
                obj.address = obj.client.shipping_address
            elif obj.client and obj.client.billing_address:
                obj.address = obj.client.billing_address
            else:
                obj.address = None

        if commit:
            obj.save()
            self.save_m2m()
            self._save_media(obj)

        return obj

    def _save_media(self, service: ServiceOrder):
        user = self.user if self.user and getattr(self.user, "is_authenticated", False) else None

        images = self.files.getlist("images")
        attachments = self.files.getlist("attachments")

        for img in images:
            ServiceOrderMedia.objects.create(
                service=service,
                file=img,
                kind=ServiceOrderMedia.Kind.IMAGE,
                original_name=getattr(img, "name", "") or "",
                uploaded_by=user,
            )

        for f in attachments:
            ServiceOrderMedia.objects.create(
                service=service,
                file=f,
                kind=ServiceOrderMedia.Kind.FILE,
                original_name=getattr(f, "name", "") or "",
                uploaded_by=user,
            )

class ServiceWorkLogForm(forms.ModelForm):
    class Meta:
        model = ServiceWorkLog
        fields = ["work_date", "hours", "workers_count", "travel_count", "materials", "performed_work"]
        widgets = {
            "work_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "hours": forms.NumberInput(attrs={"class": "form-control", "step": "0.25", "min": "0"}),
            "workers_count": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "travel_count": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "materials": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "performed_work": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, user=None, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.service = service
        if not self.is_bound:
            self.initial.setdefault("work_date", timezone.localdate())


class ServiceNoteForm(forms.ModelForm):
    class Meta:
        model = ServiceNote
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Dodaj notatkę do serwisu...",
            })
        }

    def clean_content(self):
        v = (self.cleaned_data.get("content") or "").strip()
        if not v:
            raise forms.ValidationError("Wpisz treść notatki.")
        return v
