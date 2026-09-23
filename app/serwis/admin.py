from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    ServiceOrder,
    ServiceOrderMedia,
    ServiceNote,
    ServiceActivity,
)


# ==========================================================
# MEDIA INLINE
# ==========================================================

class ServiceOrderMediaInline(admin.TabularInline):
    model = ServiceOrderMedia
    extra = 0
    readonly_fields = ("uploaded_at", "uploaded_by", "file_preview")
    fields = (
        "kind",
        "file",
        "file_preview",
        "original_name",
        "caption",
        "uploaded_by",
        "uploaded_at",
    )

    def file_preview(self, obj):
        if obj.pk and obj.kind == "image" and obj.file:
            return format_html(
                '<img src="{}" style="max-height:80px;border-radius:6px;" />',
                obj.file.url
            )
        return "-"
    file_preview.short_description = "Podgląd"


# ==========================================================
# NOTES INLINE
# ==========================================================

class ServiceNoteInline(admin.TabularInline):
    model = ServiceNote
    extra = 0
    readonly_fields = ("created_at", "author")
    fields = ("content", "is_pinned", "author", "created_at")


# ==========================================================
# ACTIVITY INLINE (READ ONLY)
# ==========================================================

class ServiceActivityInline(admin.TabularInline):
    model = ServiceActivity
    extra = 0
    can_delete = False
    readonly_fields = (
        "type",
        "title",
        "description",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False


# ==========================================================
# SERVICE ORDER ADMIN
# ==========================================================

@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):

    list_display = (
        "number",
        "title",
        "client",
        "priority_badge",
        "status_badge",
        "planned_start",
        "workers_count",
    )

    list_filter = (
        "status",
        "priority",
        "planned_start",
        "company",
    )

    search_fields = (
        "number",
        "title",
        "client__name",
    )

    readonly_fields = (
        "number",
        "display_address_admin",
        "address_street",
        "address_city",
        "address_postal_code",
        "address_country",
        "address_latitude",
        "address_longitude",
        "map_preview",
    )

    filter_horizontal = ("assigned_to",)

    inlines = [
        ServiceOrderMediaInline,
        ServiceNoteInline,
        ServiceActivityInline,
    ]

    fieldsets = (
        ("Podstawowe informacje", {
            "fields": (
                "company",
                "number",
                "title",
                "client",
                "location",
                "description",
            )
        }),
        ("Adres (snapshot)", {
            "fields": (
                "display_address_admin",
                "address_street",
                "address_postal_code",
                "address_city",
                "address_country",
                "map_preview",
            )
        }),
        ("Status i plan", {
            "fields": (
                "status",
                "status_zgrania",
                "priority",
                "planned_start",
                "planned_end",
                "assigned_to",
            )
        }),
    )

    # ------------------------------------------------------
    # OPTIMIZACJA QUERY
    # ------------------------------------------------------

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related(
            "client",
            "location",
            "address",
            "company",
        ).prefetch_related("assigned_to")
        return qs.annotate(workers_total=Count("assigned_to"))

    # ------------------------------------------------------
    # CUSTOM COLUMNS
    # ------------------------------------------------------

    def workers_count(self, obj):
        return obj.workers_total
    workers_count.short_description = "Pracownicy"

    def priority_badge(self, obj):
        colors = {
            "critical": "#dc3545",
            "high": "#dc3545",
            "normal": "#0d6efd",
            "low": "#6c757d",
        }
        color = colors.get(obj.priority, "#6c757d")
        return format_html(
            '<span style="padding:4px 8px;border-radius:6px;background:{};color:white;">{}</span>',
            color,
            obj.get_priority_display(),
        )
    priority_badge.short_description = "Priorytet"

    def status_badge(self, obj):
        colors = {
            "new": "#0d6efd",
            "in_progress": "#ffc107",
            "done": "#198754",
            "cancelled": "#6c757d",
            "zgrania": "#17a2b8",
            "forgoted": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="padding:4px 8px;border-radius:6px;background:{};color:white;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    # ------------------------------------------------------
    # SNAPSHOT ADDRESS DISPLAY
    # ------------------------------------------------------

    def display_address_admin(self, obj):
        if obj.address_street or obj.address_city or obj.address_postal_code:
            return f"{obj.address_street}, {obj.address_postal_code} {obj.address_city}"
        return "-"
    display_address_admin.short_description = "Adres serwisu"

    def map_preview(self, obj):
        if obj.address_latitude and obj.address_longitude:
            return format_html(
                '<a href="https://maps.google.com/?q={},{}" target="_blank">Otwórz w Google Maps</a>',
                obj.address_latitude,
                obj.address_longitude,
            )
        return "-"
    map_preview.short_description = "Mapa"

    # ------------------------------------------------------
    # AUTO COMPANY (multi-tenant safety)
    # ------------------------------------------------------

    def save_model(self, request, obj, form, change):
        if not obj.company_id:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)


# ==========================================================
# MEDIA ADMIN
# ==========================================================

@admin.register(ServiceOrderMedia)
class ServiceOrderMediaAdmin(admin.ModelAdmin):
    list_display = (
        "service",
        "kind",
        "original_name",
        "uploaded_by",
        "uploaded_at",
    )
    list_filter = ("kind", "uploaded_at")
    search_fields = ("original_name", "service__number")
    readonly_fields = ("uploaded_at",)


# ==========================================================
# NOTES ADMIN
# ==========================================================

@admin.register(ServiceNote)
class ServiceNoteAdmin(admin.ModelAdmin):
    list_display = (
        "service",
        "author",
        "is_pinned",
        "created_at",
    )
    list_filter = ("is_pinned", "created_at")
    search_fields = ("content", "service__number")
    readonly_fields = ("created_at",)


# ==========================================================
# ACTIVITY ADMIN
# ==========================================================

@admin.register(ServiceActivity)
class ServiceActivityAdmin(admin.ModelAdmin):
    list_display = (
        "service",
        "type",
        "title",
        "created_by",
        "created_at",
    )
    list_filter = ("type", "created_at")
    search_fields = ("title", "description", "service__number")
    readonly_fields = ("created_at",)