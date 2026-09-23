# app/gwarancja/admin.py

from django.contrib import admin
from django.utils.html import format_html

from app.gwarancja.models import (
    WarrantyClaim,
    WarrantyClaimAttachment,
    WarrantyClaimStatus,
)


class WarrantyClaimAttachmentInline(admin.TabularInline):
    model = WarrantyClaimAttachment
    extra = 0
    fields = (
        "file",
        "original_name",
        "uploaded_by",
        "created_at",
    )
    readonly_fields = (
        "created_at",
    )


@admin.register(WarrantyClaim)
class WarrantyClaimAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "external_number_display",
        "client",
        "product",
        "provider",
        "status_badge",
        "reported_at",
        "repaired_at",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "provider",
        "reported_at",
        "repaired_at",
        "created_at",
    )

    search_fields = (
        "external_number",
        "provider",
        "client__name",
        "product__name",
        "fault_description",
        "notes",
    )

    autocomplete_fields = (
        "client",
        "location",
        "product",
        "created_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Dane zgłoszenia",
            {
                "fields": (
                    "company",
                    "external_number",
                    "provider",
                    "status",
                )
            },
        ),
        (
            "Klient i urządzenie",
            {
                "fields": (
                    "client",
                    "location",
                    "product",
                )
            },
        ),
        (
            "Opis",
            {
                "fields": (
                    "fault_description",
                    "notes",
                )
            },
        ),
        (
            "Daty",
            {
                "fields": (
                    "reported_at",
                    "repaired_at",
                )
            },
        ),
        (
            "Systemowe",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    inlines = [
        WarrantyClaimAttachmentInline,
    ]

    ordering = (
        "-created_at",
    )

    actions = (
        "mark_as_reported",
        "mark_as_repaired",
    )

    def external_number_display(self, obj):
        return obj.external_number or "—"

    external_number_display.short_description = "Numer zewnętrzny"

    def status_badge(self, obj):
        colors = {
            WarrantyClaimStatus.NEW: "#6c757d",
            WarrantyClaimStatus.REPORTED: "#0d6efd",
            WarrantyClaimStatus.REPAIRED: "#198754",
        }

        labels = {
            WarrantyClaimStatus.NEW: "Nowe",
            WarrantyClaimStatus.REPORTED: "Zgłoszone",
            WarrantyClaimStatus.REPAIRED: "Naprawione",
        }
        color = colors.get(obj.status, "#6c757d")
        label = labels.get(obj.status, obj.get_status_display())

        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>',
            color,
            label,
        )

    status_badge.short_description = "Status"

    @admin.action(description="Oznacz jako zgłoszone")
    def mark_as_reported(self, request, queryset):
        for claim in queryset:
            claim.mark_reported()

    @admin.action(description="Oznacz jako naprawione")
    def mark_as_repaired(self, request, queryset):
        for claim in queryset:
            claim.mark_repaired()


@admin.register(WarrantyClaimAttachment)
class WarrantyClaimAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "claim",
        "original_name",
        "uploaded_by",
        "created_at",
    )

    search_fields = (
        "claim__external_number",
        "original_name",
        "file",
    )

    autocomplete_fields = (
        "claim",
        "uploaded_by",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )