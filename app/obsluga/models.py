# app/obsluga/models.py

from django.db import models
from django.utils import timezone

from app.core.models import CompanyOwnedModel
from app.core.fields import TrackedFileField, file_size_field
from app.core.view_permissions import view_permissions
from app.klient.models import Client, ClientLocation
from app.core.models import PanelUser
from app.dokument.models import DocumentFolder


class ServiceContractStatus(models.TextChoices):
    ACTIVE = "active", "Aktywna"
    PAUSED = "paused", "Wstrzymana"
    ENDED = "ended", "Zakończona"


class ServiceContractType(models.TextChoices):
    CCTV = "cctv", "Monitoring CCTV"
    ALARM = "alarm", "System alarmowy"
    ELECTRICAL = "electrical", "Elektryka"
    HVAC = "hvac", "Klimatyzacja / HVAC"
    IT = "it", "IT / Sieci"
    OTHER = "other", "Inne"


class ServiceContractFrequency(models.TextChoices):
    WEEKLY = "weekly", "Co tydzień"
    MONTHLY = "monthly", "Co miesiąc"
    QUARTERLY = "quarterly", "Co kwartał"
    HALF_YEARLY = "half_yearly", "Co pół roku"
    YEARLY = "yearly", "Co rok"
    CUSTOM = "custom", "Niestandardowo"


class ServiceContract(CompanyOwnedModel):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="service_contracts",
        verbose_name="Klient",
    )
    location = models.ForeignKey(
        ClientLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_contracts",
        verbose_name="Lokalizacja klienta",
    )
    title = models.CharField(max_length=255, verbose_name="Nazwa obsługi")

    contract_type = models.CharField(
        max_length=30,
        choices=ServiceContractType.choices,
        default=ServiceContractType.OTHER,
        verbose_name="Typ obsługi",
    )
    status = models.CharField(
        max_length=30,
        choices=ServiceContractStatus.choices,
        default=ServiceContractStatus.ACTIVE,
        verbose_name="Status",
    )
    frequency = models.CharField(
        max_length=30,
        choices=ServiceContractFrequency.choices,
        default=ServiceContractFrequency.MONTHLY,
        verbose_name="Częstotliwość",
    )

    start_date = models.DateField(verbose_name="Data rozpoczęcia")
    end_date = models.DateField(null=True, blank=True, verbose_name="Data zakończenia")
    next_service_date = models.DateField(null=True, blank=True, verbose_name="Następny termin")

    caretaker = models.ForeignKey(
        PanelUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_service_contracts",
        verbose_name="Opiekun",
    )

    description = models.TextField(blank=True, verbose_name="Zakres obsługi")
    notes = models.TextField(blank=True, verbose_name="Uwagi")

    monthly_price_net = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Cena miesięczna netto",
    )

    created_by = models.ForeignKey(
        PanelUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_service_contracts",
        verbose_name="Utworzył",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Obsługa"
        verbose_name_plural = "Obsługi"
        ordering = ["-created_at"]
        permissions = view_permissions(
            "service_contract_list", "service_contract_add",
            "service_contract_detail", "service_contract_asset_add",
            "service_contract_asset_update", "service_contract_asset_delete",
            "service_contract_parameter_add", "service_contract_update",
            "service_contract_parameter_update",
            "service_contract_parameter_delete", "service_visit_confirm_period",
            "service_contract_delete",
        )

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return (
            self.status == ServiceContractStatus.ACTIVE
            and self.next_service_date
            and self.next_service_date < timezone.localdate()
        )

class ServiceContractMediaType(models.TextChoices):
    IMAGE = "image", "Zdjęcie"
    FILE = "file", "Plik"


class ServiceContractMedia(models.Model):
    contract = models.ForeignKey(
        ServiceContract,
        on_delete=models.CASCADE,
        related_name="media",
        verbose_name="Obsługa",
    )

    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_contract_media",
        related_query_name="service_contract_medium",
        verbose_name="Folder",
    )

    file = TrackedFileField(
        upload_to="obsluga/media/%Y/%m/",
        verbose_name="Plik",
    )
    file_size = file_size_field()

    media_type = models.CharField(
        max_length=20,
        choices=ServiceContractMediaType.choices,
        default=ServiceContractMediaType.FILE,
        verbose_name="Typ",
    )

    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nazwa",
    )

    uploaded_by = models.ForeignKey(
        PanelUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_service_contract_media",
        verbose_name="Dodał",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Dodano",
    )

    class Meta:
        verbose_name = "Plik obsługi"
        verbose_name_plural = "Pliki obsługi"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title or self.file.name

    @property
    def is_image(self):
        return self.media_type == ServiceContractMediaType.IMAGE

class ServiceContractAssetType(models.TextChoices):
    RECORDER = "recorder", "Rejestrator"
    CAMERA = "camera", "Kamera"
    SWITCH = "switch", "Switch"
    RACK = "rack", "Szafa RACK"
    UPS = "ups", "UPS"
    ELECTRICAL_BOARD = "electrical_board", "Rozdzielnia"
    HVAC_UNIT = "hvac_unit", "Klimatyzator"
    HEAT_PUMP = "heat_pump", "Pompa ciepła"
    SENSOR = "sensor", "Czujnik"
    OTHER = "other", "Inne"


class ServiceContractAsset(models.Model):
    contract = models.ForeignKey(
        ServiceContract,
        on_delete=models.CASCADE,
        related_name="assets",
        verbose_name="Obsługa",
    )

    name = models.CharField(max_length=255, verbose_name="Nazwa elementu")

    asset_type = models.CharField(
        max_length=50,
        choices=ServiceContractAssetType.choices,
        default=ServiceContractAssetType.OTHER,
        verbose_name="Typ elementu",
    )

    location_description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Lokalizacja elementu",
        help_text="Np. strych klatka 15, serwerownia, rozdzielnia RG, sala konferencyjna.",
    )

    producer = models.CharField(max_length=150, blank=True, verbose_name="Producent")
    model = models.CharField(max_length=150, blank=True, verbose_name="Model")
    serial_number = models.CharField(max_length=150, blank=True, verbose_name="Numer seryjny")

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adres IP")
    inventory_number = models.CharField(max_length=100, blank=True, verbose_name="Numer inwentarzowy")

    notes = models.TextField(blank=True, verbose_name="Uwagi")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Element obsługi"
        verbose_name_plural = "Elementy obsługi"
        ordering = ["asset_type", "name"]

    def __str__(self):
        return self.name


class ServiceContractParameter(models.Model):
    contract = models.ForeignKey(
        ServiceContract,
        on_delete=models.CASCADE,
        related_name="parameters",
        verbose_name="Obsługa",
    )

    name = models.CharField(max_length=150, verbose_name="Nazwa parametru")
    value = models.CharField(max_length=255, blank=True, verbose_name="Wartość")
    unit = models.CharField(max_length=50, blank=True, verbose_name="Jednostka")

    group = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Grupa",
        help_text="Np. CCTV, Elektryka, Klimatyzacja, Ogólne.",
    )

    order = models.PositiveIntegerField(default=0, verbose_name="Kolejność")

    class Meta:
        verbose_name = "Parametr obsługi"
        verbose_name_plural = "Parametry obsługi"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name}: {self.value}"


class ServiceContractPerson(models.Model):
    contract = models.ForeignKey(
        ServiceContract,
        on_delete=models.CASCADE,
        related_name="people",
        verbose_name="Obsługa",
    )

    name = models.CharField(max_length=255, verbose_name="Imię i nazwisko")
    role = models.CharField(
        max_length=150,
        verbose_name="Rola",
        help_text="Np. zgrywa nagrania, kontakt techniczny, administrator obiektu.",
    )

    phone = models.CharField(max_length=50, blank=True, verbose_name="Telefon")
    email = models.EmailField(blank=True, verbose_name="E-mail")
    notes = models.TextField(blank=True, verbose_name="Uwagi")

    class Meta:
        verbose_name = "Osoba przy obsłudze"
        verbose_name_plural = "Osoby przy obsłudze"
        ordering = ["role", "name"]

    def __str__(self):
        return f"{self.name} - {self.role}"


class ChecklistTemplate(models.Model):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="checklist_templates",
    )

    name = models.CharField(max_length=255, verbose_name="Nazwa checklisty")

    contract_type = models.CharField(
        max_length=30,
        choices=ServiceContractType.choices,
        default=ServiceContractType.OTHER,
        verbose_name="Typ obsługi",
    )

    is_active = models.BooleanField(default=True, verbose_name="Aktywna")

    class Meta:
        verbose_name = "Szablon checklisty"
        verbose_name_plural = "Szablony checklist"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ChecklistTemplateItem(models.Model):
    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Szablon",
    )

    text = models.CharField(max_length=255, verbose_name="Treść punktu")
    order = models.PositiveIntegerField(default=0, verbose_name="Kolejność")
    is_required = models.BooleanField(default=False, verbose_name="Wymagane")

    class Meta:
        verbose_name = "Punkt checklisty"
        verbose_name_plural = "Punkty checklisty"
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class ServiceVisitStatus(models.TextChoices):
    PLANNED = "planned", "Zaplanowana"
    DONE = "done", "Wykonana"
    CANCELLED = "cancelled", "Anulowana"


class ServiceVisit(models.Model):
    contract = models.ForeignKey(
        ServiceContract,
        on_delete=models.CASCADE,
        related_name="visits",
        verbose_name="Obsługa",
    )

    status = models.CharField(
        max_length=30,
        choices=ServiceVisitStatus.choices,
        default=ServiceVisitStatus.PLANNED,
        verbose_name="Status",
    )

    period_start = models.DateField(null=True, blank=True, verbose_name="Początek okresu")
    period_end = models.DateField(null=True, blank=True, verbose_name="Koniec okresu")

    planned_at = models.DateField(null=True, blank=True, verbose_name="Planowana data")
    performed_at = models.DateField(null=True, blank=True, verbose_name="Data wykonania")

    title = models.CharField(max_length=255, blank=True, verbose_name="Tytuł")
    notes = models.TextField(blank=True, verbose_name="Uwagi")

    created_by = models.ForeignKey(
        PanelUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_service_visits",
        verbose_name="Utworzył",
    )

    performed_by = models.ForeignKey(
        PanelUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_service_visits",
        verbose_name="Wykonał",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Wizyta obsługi"
        verbose_name_plural = "Wizyty obsługi"
        ordering = ["-planned_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "period_start", "period_end"],
                name="unique_service_visit_period",

        )

    ]

    def __str__(self):
        return self.title or f"Wizyta - {self.contract}"


class ServiceVisitChecklistItem(models.Model):
    visit = models.ForeignKey(
        ServiceVisit,
        on_delete=models.CASCADE,
        related_name="checklist_items",
        verbose_name="Wizyta",
    )

    text = models.CharField(max_length=255, verbose_name="Treść punktu")
    is_done = models.BooleanField(default=False, verbose_name="Wykonane")
    comment = models.CharField(max_length=255, blank=True, verbose_name="Komentarz")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Punkt wykonanej checklisty"
        verbose_name_plural = "Punkty wykonanej checklisty"
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class ServiceContractActivityType(models.TextChoices):
    CREATED = "created", "Utworzono"
    UPDATED = "updated", "Zaktualizowano"
    ASSET_ADDED = "asset_added", "Dodano element"
    ASSET_UPDATED = "asset_updated", "Zmieniono element"
    ASSET_DELETED = "asset_deleted", "Usunięto element"
    PARAMETER_ADDED = "parameter_added", "Dodano parametr"
    PARAMETER_UPDATED = "parameter_updated", "Zmieniono parametr"
    PARAMETER_DELETED = "parameter_deleted", "Usunięto parametr"
    MEDIA_ADDED = "media_added", "Dodano plik"
    VISIT_CONFIRMED = "visit_confirmed", "Zatwierdzono przegląd"
    NOTE = "note", "Notatka"


class ServiceContractActivity(models.Model):
    contract = models.ForeignKey(
        ServiceContract,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="Obsługa",
    )

    activity_type = models.CharField(
        max_length=50,
        choices=ServiceContractActivityType.choices,
        default=ServiceContractActivityType.NOTE,
        verbose_name="Typ",
    )

    message = models.CharField(
        max_length=500,
        verbose_name="Opis",
    )

    created_by = models.ForeignKey(
        PanelUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_contract_activities",
        verbose_name="Użytkownik",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data",
    )

    class Meta:
        verbose_name = "Historia obsługi"
        verbose_name_plural = "Historia obsług"
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
