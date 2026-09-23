# app/products/models.py
from django.db import models
from app.core.models import CompanyOwnedModel
from app.core.fields import TrackedImageField, file_size_field
from app.core.view_permissions import view_permissions


class ProductCategory(CompanyOwnedModel):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Kategoria urzadzenia'
        verbose_name_plural = 'Kategoria urzadzenia'


class Product(CompanyOwnedModel):
    class ProductType(models.TextChoices):
        MATERIAL = "material", "Materiał"
        SERVICE = "service", "Usługa"
        ACCESSORY = "accessory", "Akcesoria"
        DEVICE = "device", "Urządzenie"
        LABOR = "labor", "Robocizna"
        OTHER = "other", "Inne"

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True)
    type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.MATERIAL
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    unit = models.CharField(max_length=20, default="szt.")
    net_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=23)  # %
    is_active = models.BooleanField(default=True)

    description = models.TextField(blank=True)

    image = TrackedImageField(
        upload_to="products/",
        null=True,
        blank=True
    )
    image_size = file_size_field("Rozmiar zdjęcia")

    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    barcode = models.CharField(
        max_length=100,
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Urzadzenie'
        verbose_name_plural = 'Urzadzenia'
        permissions = view_permissions(
            "product_create", "product_list", "product_detail",
            "product_offer_usage", "product_protocol_usage",
            "product_stock_history", "product_update",
        )

from django.conf import settings


class ProductActivity(CompanyOwnedModel):
    class Type(models.TextChoices):
        SYSTEM = "system", "System"
        CREATED = "created", "Utworzono"
        UPDATED = "updated", "Edycja"
        PRICE = "price", "Zmiana ceny"
        STATUS = "status", "Zmiana statusu"
        STOCK = "stock", "Magazyn"
        NOTE = "note", "Notatka"
        OTHER = "other", "Inne"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="Produkt",
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
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_activities",
        verbose_name="Użytkownik",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Historia produktu"
        verbose_name_plural = "Historia produktów"

    def save(self, *args, **kwargs):
        if self.product_id and not self.company_id:
            self.company = self.product.company

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product} / {self.title}"
