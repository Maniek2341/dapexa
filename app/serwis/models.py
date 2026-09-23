# app/services/models.py
from django.db import models, transaction
from django.utils import timezone

from django.core.exceptions import ValidationError
from app.core.models import Address, CompanyOwnedModel, CompanySettings
from app.core.fields import TrackedFileField, file_size_field
from app.core.view_permissions import view_permissions
from app.klient.models import Client, ClientLocation
from django.conf import settings
from app.dokument.models import DocumentFolder


def service_media_upload_to(instance, filename: str) -> str:
    company_id = getattr(instance.service, "company_id", "no-company")
    service_id = getattr(instance.service, "id", "no-id")
    return f"companies/{company_id}/services/{service_id}/media/{filename}"


class ServiceOrderMedia(models.Model):
    class Kind(models.TextChoices):
        IMAGE = "image", "Zdjęcie"
        FILE = "file", "Załącznik"

    service = models.ForeignKey("ServiceOrder", on_delete=models.CASCADE, related_name="media")
    file = TrackedFileField(upload_to=service_media_upload_to)
    file_size = file_size_field()
    kind = models.CharField(max_length=10, choices=Kind.choices)
    original_name = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=255, blank=True)

    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_media",
        related_query_name="service_medium",
        verbose_name="Folder",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="service_media_added"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = getattr(self.file, "name", "") or ""
        if self.service_id and not self.folder_id:
            folder, _ = DocumentFolder.objects.get_or_create(
                company=self.service.company,
                name="Serwisy",
                parent=None,
            )
            self.folder = folder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service_id} / {self.kind} / {self.original_name or self.file.name}"


class ServiceOrder(CompanyOwnedModel):
    class SettlementMethod(models.TextChoices):
        HOURLY = "hourly", "Godzinowo"
        PER_JOB = "per_job", "Od roboty"

    class Priority(models.TextChoices):
        LOW = "low", "Niski"
        NORMAL = "normal", "Normalny"
        HIGH = "high", "Wysoki"
        CRITICAL = "critical", "Krytyczny"

    class Status(models.TextChoices):
        NEW = "new", "Nowe"
        FORGOTED = "forgoted", "Zapomniane"
        IN_PROGRESS = "in_progress", "W trakcie"
        DONE = "done", "Zakończone"
        OBSLUGA = "zgrania", "Obsługa"
        CANCELLED = "cancelled", "Anulowane"

    class StatusZgrania(models.TextChoices):
        ZGRANIE_NEW = "new", "Nowa"
        ZGRANIE_BRAK = "nothind", "Brak materiału"
        ZGRANIE_DONE = "done", "Zakończona"
        ZGRANIE_IN_PROGRESS = "in_progress", "W trakcie"
        ZGRANIE_SEND = "send", "Zakończona i przekazana"

    number = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="services")
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    settlement_method = models.CharField(
        "Sposób rozliczenia",
        max_length=20,
        choices=SettlementMethod.choices,
        default=SettlementMethod.PER_JOB,
    )
    status_zgrania = models.CharField(
        "Status obsługi",
        max_length=20,
        choices=StatusZgrania.choices,
        default=StatusZgrania.ZGRANIE_NEW,
        blank=True,
    )
    planned_start = models.DateTimeField(null=True, blank=True)
    planned_end = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_services"
    )
    location = models.ForeignKey(
        ClientLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
        verbose_name="Lokalizacja"
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )

    # ======================================
    # 🔥 SNAPSHOT ADRESU (jak w Protocol)
    # ======================================

    address_street = models.CharField(max_length=255, blank=True)
    address_city = models.CharField(max_length=100, blank=True)
    address_postal_code = models.CharField(max_length=20, blank=True)
    address_country = models.CharField(max_length=100, blank=True)
    address_latitude = models.FloatField(null=True, blank=True)
    address_longitude = models.FloatField(null=True, blank=True)

    def snapshot_address(self, addr: "Address | None"):
        """
        Zapisuje snapshot do pól address_* na podstawie obiektu Address.
        """
        if addr:
            self.address_street = getattr(addr, "street", "") or ""
            self.address_city = getattr(addr, "city", "") or ""
            self.address_postal_code = getattr(addr, "postcode", "") or ""
            self.address_country = getattr(addr, "country", "") or ""
            self.address_latitude = getattr(addr, "latitude", None)
            self.address_longitude = getattr(addr, "longitude", None)
        else:
            self.address_street = ""
            self.address_city = ""
            self.address_postal_code = ""
            self.address_country = ""
            self.address_latitude = None
            self.address_longitude = None

    @property
    def display_address(self):
        """
        Adres do wyświetlania zawsze z snapshotu.
        """
        if self.address_street or self.address_city or self.address_postal_code:
            return f"{self.address_street}, {self.address_postal_code} {self.address_city}"
        # fallback: jakby stare rekordy nie miały snapshotu
        if self.address:
            return self.address
        if self.location and self.location.address:
            return self.location.address
        if self.client:
            return self.client.shipping_address or self.client.billing_address
        return None

    def _prefix(self, year: int) -> str:
        company_settings = CompanySettings.objects.filter(company=self.company).first()
        if self.status == self.Status.OBSLUGA:
            prefix = getattr(company_settings, "maintenance_number_prefix", "OBS")
        else:
            prefix = getattr(company_settings, "service_number_prefix", "SER")
        return f"{prefix}/{year}/"

    def _next_number(self, prefix: str) -> str:
        with transaction.atomic():
            numbers = (
                ServiceOrder.objects
                .select_for_update()
                .filter(company=self.company, number__startswith=prefix)
                .values_list("number", flat=True)
            )
            sequences = []
            for number in numbers:
                try:
                    sequences.append(int(number.rsplit("/", 1)[-1]))
                except (AttributeError, TypeError, ValueError):
                    continue
            seq = max(sequences, default=0) + 1

            company_settings = CompanySettings.objects.filter(company=self.company).first()
            digits = getattr(company_settings, "service_number_digits", 4)
            return f"{prefix}{seq:0{digits}d}"

    def __str__(self):
        return f"{self.number} - {self.title}"

    def _resolve_address(self):
        """
        Zwraca adres:
        1. z lokalizacji (jeśli wybrana)
        2. w przeciwnym razie shipping address klienta
        """
        if self.location and self.location.address:
            return self.location.address

        if self.client and self.client.shipping_address:
            return self.client.shipping_address

        return None

    @property
    def display_address(self):
        if self.location and self.location.address:
            return self.location.address
        if self.address:
            return self.address
        if self.client:
            return self.client.shipping_address or self.client.billing_address
        return None

    @property
    def display_contact_person(self):
        # 1️⃣ jeśli lokalizacja i ma osobę
        if self.location and self.location.contact_person:
            return self.location.contact_person

        # 2️⃣ jeśli brak lokalizacji → pierwsza osoba kontaktowa klienta
        if self.client:
            return self.client.contacts.order_by("id").first()

        return None

    def clean(self):
        super().clean()
        if self.pk:  # tylko po zapisaniu — ManyToMany istnieje dopiero po pk
            if self.assigned_to.count() > 3:
                raise ValidationError({"assigned_to": "Możesz przypisać maksymalnie 3 osoby do serwisu."})

        if self.pk and self.number:
            old = ServiceOrder.objects.filter(pk=self.pk).values("status", "number").first()
            if old:
                # rodzaj zgłoszenia jest niezmienny po utworzeniu
                if self.status == self.Status.OBSLUGA and old["status"] != self.Status.OBSLUGA:
                    raise ValidationError({
                        "status": "Nie można zmienić rodzaju istniejącego zgłoszenia na obsługę."
                    })

                # (opcjonalnie) blokada w drugą stronę:
                if old["status"] == self.Status.OBSLUGA and self.status != self.Status.OBSLUGA:
                    raise ValidationError({"status": "Nie można zmienić rodzaju istniejącej obsługi."})


    def save(self, *args, **kwargs):
        if not getattr(self, "company_id", None):
            raise ValueError("ServiceOrder.company musi być ustawione przed zapisem.")

        is_new = self.pk is None

        # 🔍 sprawdzamy czy zmieniono location
        location_changed = False

        if not is_new:
            old = ServiceOrder.objects.filter(pk=self.pk).values("location_id").first()
            if old and old["location_id"] != self.location_id:
                location_changed = True

        # 🔥 aktualizacja adresu:
        # - przy tworzeniu
        # - albo gdy zmieniono lokalizację
        if is_new or location_changed:
            resolved = self._resolve_address()
            self.address = resolved
            self.snapshot_address(resolved)

        # 🔥 generowanie numeru (tylko raz)
        if not self.number:
            year = timezone.now().year
            self.number = self._next_number(self._prefix(year))

        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "number"],
                name="unique_service_number_per_company",
            ),
        ]
        verbose_name = 'Zgłoszenie serwisowe'
        verbose_name_plural = 'Zgłoszenia serwisowe'
        permissions = view_permissions(
            "serwis_nowe", "serwis_add", "serwis_detail",
            "service_note_add", "service_note_pin", "service_note_delete",
            "serwis_edit", "serwis_delete", "serwis_status_update",
            "serwis_schedule_update", "serwis_assign_workers",
            "service_media_delete", "serwis_priority_update",
            "serwis_status_zgrania_update", "client_locations_api",
            "service_work_log_add",
        )


class ServiceWorkLog(CompanyOwnedModel):
    """Dzienny wpis realizacji serwisu rozliczanego godzinowo."""

    service = models.ForeignKey(
        ServiceOrder, on_delete=models.CASCADE, related_name="work_logs"
    )
    work_date = models.DateField("Dzień pracy")
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_work_logs",
    )
    hours = models.DecimalField("Godziny", max_digits=6, decimal_places=2, default=0)
    workers_count = models.PositiveIntegerField("Liczba osób", default=1)
    travel_count = models.PositiveIntegerField("Dojazdy", default=0)
    materials = models.TextField("Materiał", blank=True, default="")
    performed_work = models.TextField("Wykonane prace", blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["work_date", "created_at"]
        indexes = [models.Index(fields=["company", "service", "work_date"])]

    def clean(self):
        super().clean()
        if self.service_id and self.company_id and self.service.company_id != self.company_id:
            raise ValidationError("Serwis musi należeć do tej samej firmy co wpis.")
        if self.worker_id and self.company_id and self.worker.company_id != self.company_id:
            raise ValidationError("Pracownik musi należeć do tej samej firmy.")
        if self.service_id and self.service.settlement_method != ServiceOrder.SettlementMethod.HOURLY:
            raise ValidationError("Wpisy dzienne są dostępne tylko dla rozliczenia godzinowego.")
        if self.hours is not None and self.hours < 0:
            raise ValidationError({"hours": "Liczba godzin nie może być ujemna."})

    def __str__(self):
        return f"{self.service.number} / {self.work_date} / {self.worker}"

class ServiceNote(CompanyOwnedModel):
    service = models.ForeignKey(
        "ServiceOrder",
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="service_notes",
    )

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["company", "service", "created_at"]),
            models.Index(fields=["company", "service", "is_pinned", "created_at"]),
        ]

    def __str__(self):
        return f"ServiceNote {self.service_id} {self.created_at:%Y-%m-%d}"

class ServiceActivity(CompanyOwnedModel):
    class Type(models.TextChoices):
        SYSTEM = "system", "System"
        NOTE = "note", "Notatka"
        STATUS = "status", "Zmiana statusu"
        OTHER = "other", "Inne"

    service = models.ForeignKey(
        "ServiceOrder",
        on_delete=models.CASCADE,
        related_name="activities"
    )

    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_service_activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "service", "created_at"]),
            models.Index(fields=["company", "type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.service_id} {self.type} {self.title}".strip()
