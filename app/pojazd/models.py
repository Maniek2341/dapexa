# app/vehicles/models.py
from django.db import models
from app.core.models import CompanyOwnedModel
from app.core.fields import TrackedImageField, file_size_field
from app.core.view_permissions import view_permissions
from django.conf import settings
from app.dokument.models import DocumentFolder


class Vehicle(CompanyOwnedModel):
    registration_number = models.CharField(max_length=20, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    vin = models.CharField(max_length=50, blank=True)

    current_mileage = models.PositiveIntegerField(default=0)

    insurance_valid_until = models.DateField(
        "Ubezpieczenie ważne do",
        null=True,
        blank=True,
    )
    inspection_valid_until = models.DateField(
        "Przegląd ważny do",
        null=True,
        blank=True,
    )

    photo = TrackedImageField(
        "Zdjęcie auta",
        upload_to="vehicles/photos/",
        null=True,
        blank=True,
    )
    photo_size = file_size_field("Rozmiar zdjęcia")

    photo_folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_photos",
        related_query_name="vehicle_photo",
        verbose_name="Folder zdjęcia",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.registration_number

    def save(self, *args, **kwargs):
        if self.photo and not self.photo_folder_id and self.company_id:
            folder, _ = DocumentFolder.objects.get_or_create(
                company=self.company,
                name="Pojazdy",
                parent=None,
            )

            self.photo_folder = folder

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Pojazd"
        verbose_name_plural = "Pojazdy"
        permissions = view_permissions(
            "vehicle_create", "vehicle_detail", "vehicle_list", "vehicle_update",
            "vehicle_delete", "vehicle_event_create", "vehicle_event_delete",
            "vehicle_event_update",
        )


class VehicleEvent(CompanyOwnedModel):
    class EventType(models.TextChoices):
        REPAIR = "repair", "Naprawa"
        SERVICE = "service", "Serwis"
        DAMAGE = "damage", "Szkoda"
        INSPECTION = "inspection", "Przegląd"
        INSURANCE = "insurance", "Ubezpieczenie"
        OTHER = "other", "Inne"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Pojazd",
    )

    event_type = models.CharField(
        "Typ zdarzenia",
        max_length=20,
        choices=EventType.choices,
        default=EventType.REPAIR,
    )

    title = models.CharField("Tytuł", max_length=150)
    description = models.TextField("Opis", blank=True)

    event_date = models.DateField("Data zdarzenia")

    mileage = models.PositiveIntegerField(
        "Przebieg przy zdarzeniu",
        null=True,
        blank=True,
    )

    cost_net = models.DecimalField(
        "Koszt netto",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    photo = TrackedImageField(
        "Zdjęcie",
        upload_to="vehicles/events/",
        null=True,
        blank=True,
    )
    photo_size = file_size_field("Rozmiar zdjęcia")

    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_event_media",
        related_query_name="vehicle_event_medium",
        verbose_name="Folder",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_events",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Zdarzenie pojazdu"
        verbose_name_plural = "Zdarzenia pojazdów"
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return f"{self.vehicle} - {self.title}"

    def save(self, *args, **kwargs):
        if self.photo and not self.folder_id and self.company_id:
            parent_folder, _ = DocumentFolder.objects.get_or_create(
                company=self.company,
                name="Pojazdy",
                parent=None,
            )

            folder, _ = DocumentFolder.objects.get_or_create(
                company=self.company,
                name="Zdarzenia",
                parent=parent_folder,
            )

            self.folder = folder

        super().save(*args, **kwargs)

class VehicleChangeHistory(CompanyOwnedModel):
    class Action(models.TextChoices):
        CREATED = "created", "Utworzono"
        UPDATED = "updated", "Zaktualizowano"
        DELETED = "deleted", "Usunięto"
        EVENT_CREATED = "event_created", "Dodano zdarzenie"
        EVENT_UPDATED = "event_updated", "Edytowano zdarzenie"
        EVENT_DELETED = "event_deleted", "Usunięto zdarzenie"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="change_history",
        verbose_name="Pojazd",
    )

    event = models.ForeignKey(
        VehicleEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_history",
        verbose_name="Zdarzenie",
    )

    action = models.CharField(
        "Akcja",
        max_length=30,
        choices=Action.choices,
    )

    description = models.TextField(
        "Opis zmiany",
        blank=True,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_change_history",
        verbose_name="Zmienił",
    )

    changed_at = models.DateTimeField(
        "Data zmiany",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Historia zmian pojazdu"
        verbose_name_plural = "Historia zmian pojazdów"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.vehicle} - {self.get_action_display()}"
