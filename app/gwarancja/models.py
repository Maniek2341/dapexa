from django.db import models
from django.conf import settings
from django.utils import timezone

from app.core.models import CompanyOwnedModel
from app.core.fields import TrackedFileField, file_size_field
from app.core.view_permissions import view_permissions
from app.dokument.models import DocumentFolder



class WarrantyClaimStatus(models.TextChoices):
    NEW = "new", "Nowe"
    REPORTED = "reported", "Zgłoszone"
    REPAIRED = "repaired", "Naprawione"


class WarrantyClaim(CompanyOwnedModel):
    external_number = models.CharField(
        "Numer zgłoszenia zewnętrznego",
        max_length=100,
        db_index=True,
        blank=True,
    )

    provider = models.CharField(
        "Firma / dostawca gwarancji",
        max_length=255,
        blank=True,
    )

    client = models.ForeignKey(
        "klient.Client",
        on_delete=models.PROTECT,
        related_name="warranty_claims",
        verbose_name="Klient",
    )

    location = models.ForeignKey(
        "klient.ClientLocation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_claims",
        verbose_name="Lokalizacja",
    )

    product = models.ForeignKey(
        "urzadzenie.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_claims",
        verbose_name="Urządzenie",
    )

    status = models.CharField(
        "Status",
        max_length=20,
        choices=WarrantyClaimStatus.choices,
        default=WarrantyClaimStatus.NEW,
        db_index=True,
    )

    fault_description = models.TextField("Opis usterki", blank=True)

    reported_at = models.DateField(
        "Data zgłoszenia do gwaranta",
        null=True,
        blank=True,
    )

    repaired_at = models.DateField(
        "Data naprawy",
        null=True,
        blank=True,
    )

    notes = models.TextField("Notatki", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_warranty_claims",
        verbose_name="Utworzył",
    )

    created_at = models.DateTimeField("Utworzono", auto_now_add=True)
    updated_at = models.DateTimeField("Zaktualizowano", auto_now=True)

    class Meta:
        verbose_name = "Zgłoszenie gwarancyjne"
        verbose_name_plural = "Zgłoszenia gwarancyjne"
        ordering = ["-created_at"]
        permissions = view_permissions(
            "warranty_claim_list", "warranty_claim_create", "warranty_detail",
            "warranty_claim_mark_reported", "warranty_claim_mark_repaired",
            "warranty_delete", "warranty_edit",
        )

    def __str__(self):
        return self.external_number or f"Zgłoszenie #{self.pk}"

    def mark_reported(self, user=None, external_number=None):
        old_status = self.get_status_display()

        if external_number:
            self.external_number = external_number

        self.status = WarrantyClaimStatus.REPORTED

        if not self.reported_at:
            self.reported_at = timezone.localdate()

        self.save(update_fields=[
            "external_number",
            "status",
            "reported_at",
            "updated_at",
        ])

        self.add_activity(
            type=WarrantyClaimActivityType.REPORTED,
            title="Zgłoszenie przekazane do gwaranta",
            description=(
                f"Zmieniono status z „{old_status}” na „{self.get_status_display()}”. "
                f"Numer zewnętrzny: {self.external_number or '—'}."
            ),
            user=user,
        )


    def mark_repaired(self, user=None):
        old_status = self.get_status_display()

        self.status = WarrantyClaimStatus.REPAIRED

        if not self.repaired_at:
            self.repaired_at = timezone.localdate()

        self.save(update_fields=[
            "status",
            "repaired_at",
            "updated_at",
        ])

        self.add_activity(
            type=WarrantyClaimActivityType.REPAIRED,
            title="Zgłoszenie oznaczone jako naprawione",
            description=f"Zmieniono status z „{old_status}” na „{self.get_status_display()}”.",
            user=user,
        )

    def add_activity(self, title, description="", type="system", user=None):
        return self.activities.create(
            type=type,
            title=title,
            description=description,
            created_by=user,
        )

class WarrantyClaimAttachment(models.Model):
    claim = models.ForeignKey(
        WarrantyClaim,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Zgłoszenie",
    )

    file = TrackedFileField(
        "Plik",
        upload_to="companies/warranty_claims/files/",
    )
    file_size = file_size_field()

    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_attachments",
        related_query_name="warranty_attachment",
        verbose_name="Folder",
    )

    original_name = models.CharField("Oryginalna nazwa", max_length=255, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Dodał",
    )

    created_at = models.DateTimeField("Dodano", auto_now_add=True)

    class Meta:
        verbose_name = "Załącznik zgłoszenia gwarancyjnego"
        verbose_name_plural = "Załączniki zgłoszeń gwarancyjnych"

    def __str__(self):
        return self.original_name or self.file.name


class WarrantyClaimActivityType(models.TextChoices):
    CREATED = "created", "Utworzono"
    UPDATED = "updated", "Zaktualizowano"
    STATUS = "status", "Zmiana statusu"
    REPORTED = "reported", "Zgłoszono"
    REPAIRED = "repaired", "Naprawiono"
    FILE = "file", "Załącznik"
    NOTE = "note", "Notatka"
    SYSTEM = "system", "System"


class WarrantyClaimActivity(models.Model):
    claim = models.ForeignKey(
        WarrantyClaim,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="Zgłoszenie",
    )

    type = models.CharField(
        "Typ",
        max_length=30,
        choices=WarrantyClaimActivityType.choices,
        default=WarrantyClaimActivityType.SYSTEM,
        db_index=True,
    )

    title = models.CharField("Tytuł", max_length=255)
    description = models.TextField("Opis", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_claim_activities",
        verbose_name="Użytkownik",
    )

    created_at = models.DateTimeField("Data", auto_now_add=True)

    class Meta:
        verbose_name = "Historia zgłoszenia gwarancyjnego"
        verbose_name_plural = "Historia zgłoszeń gwarancyjnych"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
