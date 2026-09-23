# app/warehouse/models.py
from django.db import models
from app.core.models import CompanyOwnedModel
from app.core.view_permissions import view_permissions
from app.urzadzenie.models import Product


class Warehouse(CompanyOwnedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Magazyn'
        verbose_name_plural = 'Magazyny'


class StockItem(CompanyOwnedModel):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stock_items"
    )

    product = models.ForeignKey(
        "urzadzenie.Product",
        on_delete=models.CASCADE,
        related_name="stock_items"
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    min_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Minimalny stan"
    )

    class Meta:
        verbose_name = "Przedmiot na magazynie"
        verbose_name_plural = "Przedmioty na magazynie"
        unique_together = ("company", "warehouse", "product")
        permissions = view_permissions(
            "stock_list", "stock_item_create", "stock_in", "stock_out",
        )

    def __str__(self):
        return f"{self.product} @ {self.warehouse}: {self.quantity}"

    @property
    def is_below_minimum(self):
        return self.quantity < self.min_quantity


class StockMovement(CompanyOwnedModel):
    class MovementType(models.TextChoices):
        IN = "in", "Przyjęcie"
        OUT = "out", "Wydanie"
        TRANSFER = "transfer", "Przesunięcie"
        ADJUSTMENT = "adjustment", "Korekta"

    product = models.ForeignKey(
        "urzadzenie.Product",
        on_delete=models.CASCADE,
        related_name="stock_movements"
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="movements",
        null=True,
        blank=True
    )

    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="outgoing_movements",
        null=True,
        blank=True
    )

    to_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="incoming_movements",
        null=True,
        blank=True
    )

    type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)

    document_number = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Historia magazynu"
        verbose_name_plural = "Historia magazynu"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.get_type_display()} - {self.product} - {self.quantity}"
