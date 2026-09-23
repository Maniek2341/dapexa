from django.contrib import admin
from django.utils.html import format_html

from app.sprzet.models import (
    Tool,
    ToolAssignment,
    ToolEvent,
)


class ToolAssignmentInline(admin.TabularInline):
    model = ToolAssignment
    extra = 0
    fields = (
        "user",
        "assigned_at",
        "returned_at",
        "assigned_by",
        "return_condition",
        "notes",
    )
    readonly_fields = ()
    autocomplete_fields = (
        "user",
        "assigned_by",
    )


class ToolEventInline(admin.TabularInline):
    model = ToolEvent
    extra = 0
    fields = (
        "type",
        "description",
        "event_date",
        "created_by",
        "created_at",
    )
    readonly_fields = (
        "created_at",
    )
    autocomplete_fields = (
        "created_by",
    )


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "name",
        "category",
        "status",
        "manufacturer",
        "model",
        "serial_number",
        "inventory_number",
        "current_holder",
        "storage_place",
        "warranty_status",
        "next_inspection_status",
        "company",
        "created_at",
    )

    list_filter = (
        "company",
        "category",
        "status",
        "purchase_date",
        "warranty_until",
        "last_inspection_date",
        "next_inspection_date",
        "created_at",
    )

    search_fields = (
        "name",
        "manufacturer",
        "model",
        "serial_number",
        "inventory_number",
        "storage_place",
        "current_holder__first_name",
        "current_holder__last_name",
        "current_holder__email",
        "company__name",
    )

    ordering = (
        "name",
        "manufacturer",
        "model",
    )

    readonly_fields = (
        "image_preview_large",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "company",
        "current_holder",
        "created_by",
    )

    fieldsets = (
        (
            "Zdjęcie",
            {
                "fields": (
                    "image",
                    "image_preview_large",
                )
            },
        ),
        (
            "Podstawowe informacje",
            {
                "fields": (
                    "company",
                    "name",
                    "category",
                    "status",
                    "manufacturer",
                    "model",
                    "serial_number",
                    "inventory_number",
                )
            },
        ),
        (
            "Zakup i gwarancja",
            {
                "fields": (
                    "purchase_date",
                    "warranty_until",
                    "purchase_price_net",
                )
            },
        ),
        (
            "Przypisanie",
            {
                "fields": (
                    "current_holder",
                    "storage_place",
                )
            },
        ),
        (
            "Przeglądy",
            {
                "fields": (
                    "last_inspection_date",
                    "next_inspection_date",
                )
            },
        ),
        (
            "Opis i notatki",
            {
                "fields": (
                    "description",
                    "notes",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "System",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    inlines = (
        ToolAssignmentInline,
        ToolEventInline,
    )

    def image_preview(self, obj):
        if not obj.image:
            return "—"

        return format_html(
            '<img src="{}" style="width:42px;height:42px;object-fit:cover;border-radius:8px;" />',
            obj.image.url,
        )

    image_preview.short_description = "Zdjęcie"

    def image_preview_large(self, obj):
        if not obj.image:
            return "Brak zdjęcia"

        return format_html(
            '<img src="{}" style="max-width:320px;max-height:220px;object-fit:cover;border-radius:12px;" />',
            obj.image.url,
        )

    image_preview_large.short_description = "Podgląd"

    def warranty_status(self, obj):
        if not obj.warranty_until:
            return "—"

        if obj.is_warranty_active:
            return format_html(
                '<span style="color:#198754;font-weight:600;">Aktywna do {}</span>',
                obj.warranty_until.strftime("%d.%m.%Y"),
            )

        return format_html(
            '<span style="color:#6c757d;">Wygasła {}</span>',
            obj.warranty_until.strftime("%d.%m.%Y"),
        )

    warranty_status.short_description = "Gwarancja"

    def next_inspection_status(self, obj):
        if not obj.next_inspection_date:
            return "—"

        if obj.needs_inspection:
            return format_html(
                '<span style="color:#dc3545;font-weight:600;">Wymagany {}</span>',
                obj.next_inspection_date.strftime("%d.%m.%Y"),
            )

        return obj.next_inspection_date.strftime("%d.%m.%Y")

    next_inspection_status.short_description = "Następny przegląd"


@admin.register(ToolAssignment)
class ToolAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "tool",
        "user",
        "assigned_at",
        "returned_at",
        "is_active_badge",
        "assigned_by",
        "company",
    )

    list_filter = (
        "company",
        "assigned_at",
        "returned_at",
    )

    search_fields = (
        "tool__name",
        "tool__manufacturer",
        "tool__model",
        "tool__serial_number",
        "tool__inventory_number",
        "user__first_name",
        "user__last_name",
        "user__email",
        "assigned_by__first_name",
        "assigned_by__last_name",
        "assigned_by__email",
        "company__name",
    )

    ordering = (
        "-assigned_at",
    )

    autocomplete_fields = (
        "company",
        "tool",
        "user",
        "assigned_by",
    )

    fieldsets = (
        (
            "Wydanie",
            {
                "fields": (
                    "company",
                    "tool",
                    "user",
                    "assigned_at",
                    "returned_at",
                    "assigned_by",
                )
            },
        ),
        (
            "Zwrot i uwagi",
            {
                "fields": (
                    "return_condition",
                    "notes",
                )
            },
        ),
    )

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color:#0d6efd;font-weight:600;">Aktywne</span>'
            )

        return format_html(
            '<span style="color:#6c757d;">Zakończone</span>'
        )

    is_active_badge.short_description = "Status"


@admin.register(ToolEvent)
class ToolEventAdmin(admin.ModelAdmin):
    list_display = (
        "tool",
        "type",
        "event_date",
        "created_by",
        "company",
        "created_at",
    )

    list_filter = (
        "company",
        "type",
        "event_date",
        "created_at",
    )

    search_fields = (
        "tool__name",
        "tool__manufacturer",
        "tool__model",
        "tool__serial_number",
        "tool__inventory_number",
        "description",
        "created_by__first_name",
        "created_by__last_name",
        "created_by__email",
        "company__name",
    )

    ordering = (
        "-event_date",
        "-created_at",
    )

    readonly_fields = (
        "created_at",
    )

    autocomplete_fields = (
        "company",
        "tool",
        "created_by",
    )

    fieldsets = (
        (
            "Zdarzenie",
            {
                "fields": (
                    "company",
                    "tool",
                    "type",
                    "description",
                    "event_date",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "created_by",
                    "created_at",
                )
            },
        ),
    )