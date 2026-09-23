# app/warehouse/admin.py
from django.contrib import admin
from .models import Warehouse, StockItem, StockMovement


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "is_default")
    search_fields = ("name",)
    list_filter = ("company", "is_default")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "company", "quantity")
    search_fields = ("product__name", "warehouse__name")
    list_filter = ("company", "warehouse", "product")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "company", "type", "quantity", "document_number", "created_at")
    search_fields = ("product__name", "warehouse__name", "document_number")
    list_filter = ("company", "type", "warehouse")
    readonly_fields = ("created_at", "updated_at")