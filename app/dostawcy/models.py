from django.core.exceptions import ValidationError
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from app.core.models import CompanyOwnedModel
from app.core.view_permissions import view_permissions

from .fields import EncryptedTextField


class Supplier(models.Model):
    class IntegrationType(models.TextChoices):
        FEED = "feed", "Feed XML/CSV"

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=50, unique=True)
    integration_type = models.CharField(
        max_length=20, choices=IntegrationType.choices, default=IntegrationType.FEED
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SupplierProduct(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="products")
    external_id = models.CharField(max_length=255)
    sku = models.CharField(max_length=120, blank=True, db_index=True)
    ean = models.CharField(max_length=32, blank=True, db_index=True)
    name = models.CharField(max_length=500, db_index=True)
    manufacturer = models.CharField(max_length=255, blank=True, db_index=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=30, blank=True)
    vat = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    image_url = models.URLField(max_length=1000, blank=True)
    product_url = models.URLField(max_length=1000, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["supplier", "external_id"], name="supplier_product_external_unique"
        )]
        indexes = [
            models.Index(fields=["supplier", "sku"], name="supp_prod_sku_idx"),
            models.Index(fields=["supplier", "ean"], name="supp_prod_ean_idx"),
            models.Index(fields=["supplier", "manufacturer"], name="supp_prod_mfr_idx"),
            GinIndex(fields=["name"], opclasses=["gin_trgm_ops"], name="supp_prod_name_trgm"),
            GinIndex(fields=["sku"], opclasses=["gin_trgm_ops"], name="supp_prod_sku_trgm"),
            GinIndex(fields=["ean"], opclasses=["gin_trgm_ops"], name="supp_prod_ean_trgm"),
            GinIndex(fields=["manufacturer"], opclasses=["gin_trgm_ops"], name="supp_prod_mfr_trgm"),
        ]
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class SupplierIntegration(CompanyOwnedModel):
    class FeedType(models.TextChoices):
        XML = "xml", "XML"
        CSV = "csv", "CSV"

    class SyncStatus(models.TextChoices):
        NEVER = "never", "Nie uruchomiono"
        QUEUED = "queued", "Oczekuje"
        RUNNING = "running", "W trakcie"
        SUCCESS = "success", "Zakończono"
        PARTIAL = "partial", "Zakończono z błędami"
        ERROR = "error", "Błąd"

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="integrations")
    name = models.CharField(max_length=160)
    feed_url = EncryptedTextField()
    feed_type = models.CharField(max_length=8, choices=FeedType.choices, default=FeedType.XML)
    is_active = models.BooleanField(default=False)
    sync_catalog = models.BooleanField(default=True)
    sync_prices = models.BooleanField(default=True)
    sync_stock = models.BooleanField(default=True)
    default_markup = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(
        max_length=12, choices=SyncStatus.choices, default=SyncStatus.NEVER
    )
    last_sync_error = models.TextField(blank=True)
    last_sync_processed = models.PositiveIntegerField(default=0)
    last_sync_added = models.PositiveIntegerField(default=0)
    last_sync_updated = models.PositiveIntegerField(default=0)
    last_sync_errors = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["company", "supplier"], name="supplier_integration_company_unique"
        )]
        permissions = view_permissions(
            "supplier_integrations", "supplier_integration_save",
            "supplier_integration_sync", "supplier_catalog", "supplier_product_add",
        )
        ordering = ["supplier__name"]

    def __str__(self):
        return f"{self.company_id}:{self.supplier}"

    def clean(self):
        super().clean()
        if self.feed_url and not self.feed_url.startswith(("https://", "http://")):
            raise ValidationError({"feed_url": "Feed musi być adresem HTTP lub HTTPS."})


class SupplierCompanyProduct(CompanyOwnedModel):
    """Company-specific offer and stock values for one global supplier product."""

    integration = models.ForeignKey(
        SupplierIntegration, on_delete=models.CASCADE, related_name="company_products"
    )
    supplier_product = models.ForeignKey(
        SupplierProduct, on_delete=models.CASCADE, related_name="company_records"
    )
    purchase_price_net = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    stock_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    availability = models.BooleanField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    local_product = models.ForeignKey(
        "urzadzenie.Product", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="supplier_links",
    )

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["integration", "supplier_product"], name="supplier_company_product_unique"
        )]
        indexes = [
            models.Index(fields=["company", "supplier_product"], name="supp_comp_prod_idx"),
            models.Index(fields=["company", "last_sync_at"], name="supp_comp_sync_idx"),
        ]

    def clean(self):
        if self.integration_id and self.company_id != self.integration.company_id:
            raise ValidationError("Firma musi być zgodna z integracją.")
        if (
            self.integration_id and self.supplier_product_id
            and self.integration.supplier_id != self.supplier_product.supplier_id
        ):
            raise ValidationError("Produkt musi należeć do dostawcy tej integracji.")
        if self.local_product_id and self.local_product.company_id != self.company_id:
            raise ValidationError({"local_product": "Produkt musi należeć do tej firmy."})

    def save(self, *args, **kwargs):
        if self.integration_id:
            self.company_id = self.integration.company_id
        self.full_clean(exclude=None)
        return super().save(*args, **kwargs)
