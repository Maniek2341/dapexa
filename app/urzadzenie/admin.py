# app/products/admin.py
from django.contrib import admin
from .models import ProductCategory, Product


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "parent")
    search_fields = ("name",)
    list_filter = ("company",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "sku", "type", "category", "unit", "net_price", "vat_rate", "is_active")
    search_fields = ("name", "sku")
    list_filter = ("company", "type", "category", "is_active")
    readonly_fields = ("created_at", "updated_at")