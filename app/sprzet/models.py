# app/sprzet/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

from app.core.models import CompanyOwnedModel
from app.core.fields import TrackedImageField, file_size_field
from app.core.view_permissions import view_permissions
from app.dokument.models import DocumentFolder


def tool_image_upload_path(instance, filename):
    return f"firmy/{instance.company_id}/sprzet/{instance.pk or 'new'}/{filename}"

class ToolStatus(models.TextChoices):
    AVAILABLE = "available", "Dostępne"
    IN_USE = "in_use", "W użyciu"
    SERVICE = "service", "W serwisie"
    DAMAGED = "damaged", "Uszkodzone"
    LOST = "lost", "Zagubione"
    RETIRED = "retired", "Wycofane"


class ToolCategory(models.TextChoices):
    POWER_TOOL = "power_tool", "Elektronarzędzie"
    HAND_TOOL = "hand_tool", "Narzędzie ręczne"
    MEASUREMENT = "measurement", "Pomiarowe"
    LADDER = "ladder", "Drabiny / podesty"
    SAFETY = "safety", "BHP"
    OTHER = "other", "Inne"


class Tool(CompanyOwnedModel):
    image = TrackedImageField(
        upload_to=tool_image_upload_path,
        null=True,
        blank=True,
        verbose_name="Zdjęcie narzędzia",
    )
    image_size = file_size_field("Rozmiar zdjęcia")

    name = models.CharField(
        max_length=160,
        verbose_name="Nazwa",
    )

    category = models.CharField(
        max_length=40,
        choices=ToolCategory.choices,
        default=ToolCategory.POWER_TOOL,
        verbose_name="Kategoria",
    )

    status = models.CharField(
        max_length=40,
        choices=ToolStatus.choices,
        default=ToolStatus.AVAILABLE,
        verbose_name="Status",
    )

    manufacturer = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Producent",
    )

    model = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Model",
    )

    serial_number = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Numer seryjny",
    )

    inventory_number = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Numer ewidencyjny",
    )

    purchase_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data zakupu",
    )

    warranty_until = models.DateField(
        null=True,
        blank=True,
        verbose_name="Gwarancja do",
    )

    purchase_price_net = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cena zakupu netto",
    )

    current_holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="held_tools",
        verbose_name="Aktualnie u pracownika",
    )

    storage_place = models.CharField(
        max_length=160,
        blank=True,
        verbose_name="Miejsce przechowywania",
        help_text="Np. magazyn, auto serwisowe, biuro.",
    )

    last_inspection_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Ostatni przegląd",
    )

    next_inspection_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Następny przegląd",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Opis",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Notatki wewnętrzne",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tools",
        verbose_name="Utworzył",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    folder = models.ForeignKey(
            DocumentFolder,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="tool_images",
            related_query_name="tool_image",
            verbose_name="Folder zdjęcia",
        )

    class Meta:
        verbose_name = "Narzędzie"
        verbose_name_plural = "Narzędzia"
        ordering = ["name", "manufacturer", "model"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "category"]),
            models.Index(fields=["serial_number"]),
            models.Index(fields=["inventory_number"]),
        ]
        permissions = view_permissions(
            "tool_list", "tool_create", "tool_detail", "tool_event_add",
            "tool_update", "tool_delete",
        )
        
    def __str__(self):
        if self.manufacturer or self.model:
            return f"{self.name} — {self.manufacturer} {self.model}".strip()
        return self.name
    
    def save(self, *args, **kwargs):
        if self.image and not self.folder_id and self.company_id:
            folder, _ = DocumentFolder.objects.get_or_create(
                company=self.company,
                name="Sprzęt",
                parent=None,
            )
            self.folder = folder
        super().save(*args, **kwargs)

    @property
    def is_warranty_active(self):
        return bool(
            self.warranty_until
            and self.warranty_until >= timezone.localdate()
        )

    @property
    def needs_inspection(self):
        return bool(
            self.next_inspection_date
            and self.next_inspection_date <= timezone.localdate()
        )

class ToolAssignment(CompanyOwnedModel):
    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="Narzędzie",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tool_assignments",
        verbose_name="Pracownik",
    )

    assigned_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Wydano",
    )

    returned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Zwrócono",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_tool_assignments",
        verbose_name="Wydał",
    )

    return_condition = models.TextField(
        blank=True,
        verbose_name="Stan przy zwrocie",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Uwagi",
    )

    class Meta:
        verbose_name = "Wydanie narzędzia"
        verbose_name_plural = "Wydania narzędzi"
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.tool} → {self.user}"

    @property
    def is_active(self):
        return self.returned_at is None


class ToolEventType(models.TextChoices):
    REPAIR = "repair", "Naprawa"
    SERVICE = "service", "Serwis"
    DAMAGE = "damage", "Szkoda"
    OTHER = "other", "Inne"


class ToolEvent(CompanyOwnedModel):
    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Sprzęt",
    )

    type = models.CharField(
        max_length=30,
        choices=ToolEventType.choices,
        default=ToolEventType.REPAIR,
        verbose_name="Typ zdarzenia",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Opis",
    )

    event_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data zdarzenia",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tool_events",
        verbose_name="Utworzył",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Zdarzenie sprzętu"
        verbose_name_plural = "Zdarzenia sprzętu"
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return f"{self.tool} — {self.get_type_display()}"


def tool_event_media_upload_path(instance, filename):
    return (
        f"firmy/{instance.company_id}/sprzet/"
        f"{instance.event.tool_id}/events/{instance.event_id}/{filename}"
    )


class ToolEventMedia(CompanyOwnedModel):
    event = models.ForeignKey(
        ToolEvent,
        on_delete=models.CASCADE,
        related_name="media",
        verbose_name="Zdarzenie",
    )

    image = TrackedImageField(
        upload_to=tool_event_media_upload_path,
        verbose_name="Zdjęcie",
    )
    image_size = file_size_field("Rozmiar zdjęcia")

    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tool_event_media",
        related_query_name="tool_event_medium",
        verbose_name="Folder",
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Opis zdjęcia",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_tool_event_media",
        verbose_name="Dodał",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Zdjęcie zdarzenia sprzętu"
        verbose_name_plural = "Zdjęcia zdarzeń sprzętu"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.event} — zdjęcie"

    def save(self, *args, **kwargs):
        if self.event_id and not self.folder_id:
            folder, _ = DocumentFolder.objects.get_or_create(
                company=self.company,
                name="Sprzęt",
                parent=None,
            )
            self.folder = folder

        super().save(*args, **kwargs)


class ToolHistoryType(models.TextChoices):
    CREATED = "created", "Utworzono"
    UPDATED = "updated", "Zaktualizowano"
    STATUS = "status", "Zmiana statusu"
    HOLDER = "holder", "Zmiana przypisania"
    DELETED = "deleted", "Usunięto"
    OTHER = "other", "Inne"


class ToolHistory(CompanyOwnedModel):
    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name="Narzędzie",
    )

    type = models.CharField(
        max_length=30,
        choices=ToolHistoryType.choices,
        default=ToolHistoryType.UPDATED,
        verbose_name="Typ wpisu",
    )

    title = models.CharField(
        max_length=180,
        verbose_name="Tytuł",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Opis",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tool_history",
        verbose_name="Utworzył",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data",
    )

    class Meta:
        verbose_name = "Historia narzędzia"
        verbose_name_plural = "Historie narzędzi"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool} — {self.title}"
