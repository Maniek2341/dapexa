from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Max
from app.core.models import CompanyOwnedModel
from app.core.fields import TrackedFileField, TrackedImageField, file_size_field
from app.core.view_permissions import view_permissions
from django.utils import timezone
from django.db import transaction
# app/offers/models.py
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from app.dokument.models import DocumentFolder

from app.core.models import CompanyOwnedModel

class OfferNumberCounter(models.Model):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="offer_counters",
    )
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("company", "year")
        verbose_name = "Licznik numerów ofert"
        verbose_name_plural = "Liczniki numerów ofert"

    def __str__(self):
        return f"{self.company} / {self.year} / {self.last_number}"


class Offer(CompanyOwnedModel):
    STATUS_NOWE = 1
    STATUS_PRZYGOTOWANE = 2
    STATUS_WYSLANE = 3
    STATUS_NIEAKTUALNE = 4
    STATUS_PRZEKAZANE = 5
    STATUS_SPOTKANIE = 6
    STATUS_DOZROBIENIA = 7

    STATUS_CHOICES = [
        (STATUS_NOWE, "Nowe"),
        (STATUS_SPOTKANIE, "Spotkanie"),
        (STATUS_DOZROBIENIA, "Do zrobienia"),
        (STATUS_PRZYGOTOWANE, "Przygotowane"),
        (STATUS_WYSLANE, "Wysłane"),
        (STATUS_NIEAKTUALNE, "Nieaktualne"),
        (STATUS_PRZEKAZANE, "Przekazane do realizacji"),
    ]

    class Priority(models.TextChoices):
        LOW = "low", "Niski"
        NORMAL = "normal", "Normalny"
        HIGH = "high", "Wysoki"
        CRITICAL = "critical", "Krytyczny"

    client = models.ForeignKey(
        "klient.Client",
        on_delete=models.CASCADE,
        related_name="offers",
        verbose_name="Klient",
    )

    location = models.ForeignKey(
        "klient.ClientLocation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="offers",
        verbose_name="Lokalizacja",
    )
    number = models.CharField(max_length=50, verbose_name="Numer oferty")
    title = models.CharField(max_length=255, verbose_name="Tytuł")
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        default=STATUS_NOWE,
        verbose_name="Status",
    )

    issue_date = models.DateField(verbose_name="Data wystawienia")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Ważna do")

    order_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Numer zamówienia",
    )
    is_ordered = models.BooleanField(default=False, verbose_name="Czy zamówiono")

    sent_to_client_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data wysłania do klienta",
    )
    forwarded_to_execution_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data przekazania do realizacji",
    )

    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Powód odrzucenia / nieaktualności",
    )

    description = models.TextField(blank=True, verbose_name="Opis")
    notes = models.TextField(blank=True, verbose_name="Notatki")

    meeting_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data i czas spotkania",
    )

    assigned_employees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_offers",
        verbose_name="Przypisani pracownicy",
    )

    employees_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Ilu pracowników",
    )

    post_meeting_notes = models.TextField(
        blank=True,
        verbose_name="Informacje po spotkaniu",
    )
    
    labor_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Ilość roboczogodzin",
    )
    execution_days = models.PositiveIntegerField(
        default=0,
        verbose_name="Ilość dni na wykonanie",
    )

    has_warranty = models.BooleanField(default=False, verbose_name="Czy jest gwarancja")
    has_service = models.BooleanField(default=False, verbose_name="Czy jest obsługa")

    approved_by_manager = models.BooleanField(
        default=False,
        verbose_name="Czy oferta zatwierdzona przez szefa/menadżera",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data zatwierdzenia",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_offers",
        verbose_name="Zatwierdził",
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name="Priorytet",
    )

    order_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data zamówienia",
    )

    execution_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data wykonania",
    )

    @classmethod
    def generate_number(cls, company):
        year = timezone.now().year

        with transaction.atomic():
            counter, _ = OfferNumberCounter.objects.select_for_update().get_or_create(
                company=company,
                year=year,
                defaults={"last_number": 0},
            )
            counter.last_number += 1
            counter.save(update_fields=["last_number"])

            return f"OF/{year}/{counter.last_number:04d}"

    class Meta:
        ordering = ["-issue_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "number"],
                name="unique_offer_number_per_company",
            )
        ]
        verbose_name = "Oferta"
        verbose_name_plural = "Oferty"
        permissions = view_permissions(
            "offer_create", "offer_list", "offer_edit", "offer_delete",
            "offer_forward_to_execution", "offer_detail",
            "offer_client_locations_api", "offer_status_update", "offer_approve",
            "offer_variant_add", "offer_variant_edit", "offer_variant_delete",
            "offer_variant_toggle_selected", "offer_priority_update",
            "offer_assign_workers",
        )

    def clean(self):
        super().clean()

        if self.approved_by and self.approved_by.company_id != self.company_id:
            raise ValidationError({
                "approved_by": "Zatwierdzający musi należeć do tej samej firmy."
            })

        if self.location and self.client_id and self.location.client_id != self.client_id:
            raise ValidationError({
                "location": "Wybrana lokalizacja nie należy do tego klienta."
            })

    def save(self, *args, **kwargs):
        if not self.number and self.company_id:
            self.number = self.generate_number(self.company)

        if self.status == self.STATUS_WYSLANE and not self.sent_to_client_at:
            self.sent_to_client_at = timezone.now().date()

        if self.status == self.STATUS_PRZEKAZANE and not self.forwarded_to_execution_at:
            self.forwarded_to_execution_at = timezone.now().date()

        if self.is_ordered and not self.order_date:
            self.order_date = timezone.now().date()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number} - {self.title}"


class OfferVariant(CompanyOwnedModel):
    class SourceType(models.TextChoices):
        PDF = "pdf", "PDF"
        ITEMS = "items", "Pozycje"

    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="Oferta",
    )

    source_type = models.CharField(
        max_length=10,
        choices=SourceType.choices,
        default=SourceType.ITEMS,
        verbose_name="Sposób utworzenia",
    )
    name = models.CharField(max_length=120, verbose_name="Nazwa wariantu")
    description = models.TextField(blank=True, verbose_name="Opis")

    is_selected = models.BooleanField(default=False, verbose_name="Wybrany")
    selected_at = models.DateTimeField(null=True, blank=True, verbose_name="Data wyboru")

    materials_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Materiały netto")
    accessories_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Akcesoria netto")
    labor_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Robocizna netto")
    services_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Usługi netto")
    other_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Inne netto")

    total_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Razem netto")
    total_vat = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="VAT")
    total_brutto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Razem brutto")
    sale_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Cena sprzedaży netto")

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["offer", "name"],
                name="unique_variant_name_per_offer",
            )
        ]
        verbose_name = "Wariant oferty"
        verbose_name_plural = "Warianty ofert"

    def clean(self):
        super().clean()
        if self.offer_id and self.company_id and self.offer.company_id != self.company_id:
            raise ValidationError("Firma wariantu musi być taka sama jak firma oferty.")

    def recalculate_totals(self):
        items = list(self.items.all())

        self.materials_netto = sum(
            (item.total_netto for item in items if item.item_type == OfferVariantItem.ItemType.MATERIAL),
            Decimal("0"),
        )
        self.accessories_netto = sum(
            (item.total_netto for item in items if item.item_type == OfferVariantItem.ItemType.ACCESSORY),
            Decimal("0"),
        )
        self.services_netto = sum(
            (item.total_netto for item in items if item.item_type == OfferVariantItem.ItemType.SERVICE),
            Decimal("0"),
        )

        self.total_netto = (
            self.materials_netto
            + self.accessories_netto
            + self.labor_netto
            + self.services_netto
            + self.other_netto
        )
        self.total_vat = sum((item.vat_value for item in items), Decimal("0"))
        self.total_brutto = self.total_netto + self.total_vat

        self.save(update_fields=[
            "materials_netto",
            "accessories_netto",
            "labor_netto",
            "services_netto",
            "other_netto",
            "total_netto",
            "total_vat",
            "total_brutto",
        ])

    @property
    def costs_netto(self):
        return (
            (self.materials_netto or Decimal("0"))
            + (self.accessories_netto or Decimal("0"))
            + (self.labor_netto or Decimal("0"))
            + (self.other_netto or Decimal("0"))
        )

    @property
    def profit(self):
        return (
            (self.total_netto or Decimal("0"))
            - (self.materials_netto or Decimal("0"))
            - (self.accessories_netto or Decimal("0"))
        )

    @property
    def margin_percent(self):
        if not self.total_netto:
            return Decimal("0")

        return (
            (self.profit / self.total_netto) * Decimal("100")
        ).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        if self.offer_id and not self.company_id:
            self.company = self.offer.company

        if self.is_selected and not self.selected_at:
            self.selected_at = timezone.now()
        elif not self.is_selected:
            self.selected_at = None

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.offer.number} / {self.name}"


class OfferVariantItem(CompanyOwnedModel):
    class ItemType(models.TextChoices):
        MATERIAL = "material", "Materiał"
        ACCESSORY = "accessory", "Akcesoria"
        SERVICE = "service", "Usługa"

    variant = models.ForeignKey(OfferVariant, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    name = models.CharField(max_length=255)
    product = models.ForeignKey(
        "urzadzenie.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="offer_items",
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, default="szt.")
    unit_price_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=23)
    total_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_brutto = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def clean(self):
        super().clean()
        if self.variant_id and self.company_id and self.variant.company_id != self.company_id:
            raise ValidationError("Firma pozycji musi być taka sama jak firma wariantu.")

    def save(self, *args, **kwargs):
        if self.variant_id and not self.company_id:
            self.company = self.variant.company

        qty = self.quantity or Decimal("0")
        price = self.unit_price_netto or Decimal("0")
        vat = self.vat_rate or Decimal("0")

        self.total_netto = qty * price
        self.vat_value = self.total_netto * (vat / Decimal("100"))
        self.total_brutto = self.total_netto + self.vat_value

        super().save(*args, **kwargs)

        if self.variant_id:
            self.variant.recalculate_totals()

    def delete(self, *args, **kwargs):
        variant = self.variant if self.variant_id else None
        super().delete(*args, **kwargs)

        if variant:
            variant.recalculate_totals()

    def __str__(self):
        return self.name

def offer_variant_file_path(instance, filename):
    return (
        f"companies/{instance.variant.offer.company_id}/"
        f"offers/{instance.variant.offer_id}/"
        f"variants/{instance.variant_id}/{filename}"
    )


class OfferVariantFile(CompanyOwnedModel):
    variant = models.ForeignKey(OfferVariant, on_delete=models.CASCADE, related_name="files")
    file = TrackedFileField(
        upload_to=offer_variant_file_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    file_size = file_size_field()

    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offer_variant_files",
        related_query_name="offer_variant_file",
        verbose_name="Folder",
    )

    title = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def clean(self):
        super().clean()
        if self.variant_id and self.company_id and self.variant.company_id != self.company_id:
            raise ValidationError("Firma pliku musi być taka sama jak firma wariantu.")

    def save(self, *args, **kwargs):
        if self.variant_id and not self.company_id:
            self.company = self.variant.company
        if not self.folder_id and self.company_id:
            folder, _ = DocumentFolder.objects.get_or_create(
                company=self.company,
                name="Oferty",
                parent=None,
            )
            self.folder = folder

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or self.file.name


def offer_image_file_path(instance, filename):
    return (
        f"companies/{instance.offer.company_id}/"
        f"offers/{instance.offer_id}/"
        f"images/{filename}"
    )


class OfferImage(CompanyOwnedModel):
    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Oferta",
    )
    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offer_images",
        related_query_name="offer_image",
        verbose_name="Folder",
    )

    file = TrackedImageField(
        upload_to=offer_image_file_path,
        verbose_name="Zdjęcie",
    )
    file_size = file_size_field("Rozmiar zdjęcia")

    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Dodano")

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        verbose_name = "Zdjęcie oferty"
        verbose_name_plural = "Zdjęcia ofert"

    def clean(self):
        super().clean()
        if self.offer_id and self.company_id and self.offer.company_id != self.company_id:
            raise ValidationError("Firma zdjęcia musi być taka sama jak firma oferty.")

    def save(self, *args, **kwargs):
        if self.offer_id and not self.company_id:
            self.company = self.offer.company
        if not self.folder_id and self.company_id:
            folder, _ = DocumentFolder.objects.get_or_create(
                company=self.company,
                name="Oferty",
                parent=None,
            )
            self.folder = folder

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Zdjęcie oferty {self.offer.number}"


class OfferActivity(CompanyOwnedModel):
    class Type(models.TextChoices):
        NOTE = "note", "Notatka"
        STATUS = "status", "Zmiana statusu"
        VARIANT = "variant", "Wariant"
        FILE = "file", "Plik"
        IMAGE = "image", "Zdjęcie"
        WORKERS = "workers", "Pracownicy"
        PRIORITY = "priority", "Priorytet"
        APPROVAL = "approval", "Zatwierdzenie"
        SYSTEM = "system", "System"

    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="Oferta",
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM,
        verbose_name="Typ",
    )
    title = models.CharField(max_length=255, verbose_name="Tytuł")
    description = models.TextField(blank=True, verbose_name="Opis")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="offer_activities",
        verbose_name="Użytkownik",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data")

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Historia oferty"
        verbose_name_plural = "Historia ofert"

    def save(self, *args, **kwargs):
        if self.offer_id and not self.company_id:
            self.company = self.offer.company
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.offer.number} / {self.title}"
