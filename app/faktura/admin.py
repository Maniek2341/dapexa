# app/invoices/admin.py
from django.contrib import admin
from .models import VatExemptionReason, Invoice, InvoiceItem


@admin.register(VatExemptionReason)
class VatExemptionReasonAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "number", "company", "client", "issue_date", "sale_date",
        "due_date", "payment_method", "vat_mode", "ksef_status",
    )
    search_fields = ("number", "client__name", "ksef_number")
    list_filter = ("company", "vat_mode", "issue_date", "due_date")
    inlines = [InvoiceItemInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "company", "name", "quantity", "unit", "net_price", "vat_rate", "is_vat_exempt")
    search_fields = ("invoice__number", "name", "pkwiu")
    list_filter = ("company", "vat_rate", "is_vat_exempt")
    readonly_fields = ("created_at", "updated_at")