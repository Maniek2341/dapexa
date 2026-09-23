from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    Client,
    ContactPerson,
    ClientLocation,
    ClientActivity,
    ClientNote,
)


# ==========================================================
# CONTACT PERSON INLINE
# ==========================================================

class ContactPersonInline(admin.TabularInline):
    model = ContactPerson
    extra = 0
    fields = ("first_name", "last_name", "email", "phone")


# ==========================================================
# LOCATION INLINE
# ==========================================================

class ClientLocationInline(admin.TabularInline):
    model = ClientLocation
    extra = 0
    fields = (
        "name",
        "code",
        "address",
        "contact_person",
        "is_default",
        "is_active",
    )


# ==========================================================
# NOTES INLINE
# ==========================================================

class ClientNoteInline(admin.TabularInline):
    model = ClientNote
    extra = 0
    readonly_fields = ("created_at", "author")
    fields = ("content", "is_pinned", "author", "created_at")


# ==========================================================
# ACTIVITY INLINE (READ ONLY)
# ==========================================================

class ClientActivityInline(admin.TabularInline):
    model = ClientActivity
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
# CLIENT ADMIN
# ==========================================================

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):

    list_display = (
        "display_name",
        "client_type",
        "email",
        "phone",
        "caretaker",
        "locations_count",
        "is_active",
    )

    list_filter = (
        "client_type",
        "is_active",
        "company",
    )

    search_fields = (
        "name",
        "first_name",
        "last_name",
        "nip",
        "email",
        "phone",
    )

    readonly_fields = ()

    inlines = [
        ContactPersonInline,
        ClientLocationInline,
        ClientNoteInline,
        ClientActivityInline,
    ]

    fieldsets = (
        ("Podstawowe informacje", {
            "fields": (
                "company",
                "client_type",
                "name",
                ("first_name", "last_name"),
                "nip",
            )
        }),
        ("Kontakt", {
            "fields": (
                "email",
                "phone",
                "caretaker",
            )
        }),
        ("Adresy", {
            "fields": (
                "billing_address",
                "shipping_address",
            )
        }),
        ("Dodatkowe", {
            "fields": (
                "notes",
                "is_active",
            )
        }),
    )

    # ------------------------------------------------------
    # OPTIMIZED QUERYSET
    # ------------------------------------------------------

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related(
            "caretaker",
            "company",
        ).prefetch_related("locations")
        return qs.annotate(loc_total=Count("locations"))

    def locations_count(self, obj):
        return obj.loc_total
    locations_count.short_description = "Lokalizacje"

    def display_name(self, obj):
        return str(obj)
    display_name.short_description = "Nazwa klienta"

    # ------------------------------------------------------
    # AUTO COMPANY
    # ------------------------------------------------------

    def save_model(self, request, obj, form, change):
        if not obj.company_id:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)


# ==========================================================
# CONTACT PERSON ADMIN
# ==========================================================

@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "client",
        "email",
        "phone",
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "client__name",
    )
    list_filter = ("company",)


# ==========================================================
# CLIENT LOCATION ADMIN
# ==========================================================

@admin.register(ClientLocation)
class ClientLocationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "client",
        "contact_person",
        "is_default",
        "is_active",
    )

    list_filter = (
        "is_default",
        "is_active",
        "company",
    )

    search_fields = (
        "name",
        "code",
        "client__name",
    )

    autocomplete_fields = (
        "client",
        "contact_person",
        "address",
    )

    def save_model(self, request, obj, form, change):
        if not obj.company_id:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)


# ==========================================================
# CLIENT NOTE ADMIN
# ==========================================================

@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "author",
        "is_pinned",
        "created_at",
    )
    list_filter = ("is_pinned", "created_at", "company")
    search_fields = ("content", "client__name")
    readonly_fields = ("created_at",)


# ==========================================================
# CLIENT ACTIVITY ADMIN
# ==========================================================

@admin.register(ClientActivity)
class ClientActivityAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "type",
        "title",
        "created_by",
        "created_at",
    )
    list_filter = ("type", "created_at", "company")
    search_fields = ("title", "description", "client__name")
    readonly_fields = ("created_at",)