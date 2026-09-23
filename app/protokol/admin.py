from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from .models import (
    Protocol,
    ProtokolUrzadzenia,
    ProtokolImage,
    ProtocolActivity,
)


# =========================================================
# 🔹 INLINE: URZĄDZENIA
# =========================================================

class ProtokolUrzadzeniaInline(admin.TabularInline):
    model = ProtokolUrzadzenia
    extra = 1
    autocomplete_fields = ["urzadzenia"]


# =========================================================
# 🔹 INLINE: PLIKI / ZDJĘCIA
# =========================================================

class ProtokolImageInline(admin.TabularInline):
    model = ProtokolImage
    extra = 0
    readonly_fields = ("uploaded_by", "uploaded_at", "preview")

    fields = (
        "file",
        "preview",
        "kind",
        "caption",
        "uploaded_by",
        "uploaded_at",
    )

    def preview(self, obj):
        if obj.file and obj.kind == ProtokolImage.Kind.IMAGE:
            return format_html(
                '<img src="{}" style="max-height: 120px;" />',
                obj.file.url
            )
        return "-"
    preview.short_description = "Podgląd"


# =========================================================
# 🔹 INLINE: AKTYWNOŚĆ
# =========================================================

class ProtocolActivityInline(admin.TabularInline):
    model = ProtocolActivity
    extra = 0
    readonly_fields = ("created_at", "created_by")
    ordering = ("-created_at",)


# =========================================================
# 🔹 PROTOCOL ADMIN
# =========================================================

@admin.register(Protocol)
class ProtocolAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "client",
        "status",
        "rodzaj_prac",
        "net_total",
        "signed_by_client",
        "created_at",
    )

    list_filter = (
        "status",
        "rodzaj_prac",
        "signed_by_client",
        "ile_vat",
        "created_at",
    )

    search_fields = (
        "number",
        "client__name",
        "opis",
        "wykonane_prace",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "end_time",
        "net_total",
    )

    autocomplete_fields = (
        "client",
        "pracownik",
        "service",
        "address",
        "location",
    )

    inlines = [
        ProtokolUrzadzeniaInline,
        ProtokolImageInline,
        ProtocolActivityInline,
    ]

    fieldsets = (

        ("📄 Podstawowe informacje", {
            "fields": (
                "company",
                "number",
                "status",
                "service",
                "client",
                "pracownik",
                "rodzaj_prac",
                "title",
            )
        }),

        ("🛠 Szczegóły wykonania", {
            "fields": (
                "wykonane_prace",
                "opis",
                "dodatkowe_materialy",
                "dodatkowe_info_pracownik",
                "dodatkowy_komentarz",
            )
        }),

        ("📍 Lokalizacja", {
            "fields": (
                "address",
                "address_street",
                "address_city",
                "address_postal_code",
                "address_country",
                "address_latitude",
                "address_longitude",
                "location",
            )
        }),

        ("🚗 Dojazd", {
            "fields": (
                "distance_km",
                "travel_cost",
                "dojazdy_szt",
            )
        }),

        ("👷 Robocizna", {
            "fields": (
                "labor_cost",
                "robocizna",
                "pracownicy_szt",
            )
        }),

        ("🧾 Podsumowanie", {
            "fields": (
                "ile_vat",
                "protokol_ceny",
                "protokol_bez_ceny",
                "czy_powykonawcza",
                "sposob_wysylki",
                "net_total",
            )
        }),

        ("✍ Podpisy", {
            "fields": (
                "signed_by_client",
                "client_signature",
                "signed_by_employee",
                "employee_signature",
            )
        }),

        ("⚙ System", {
            "fields": (
                "is_active",
                "is_praca",
                "created_at",
                "updated_at",
                "end_time",
            )
        }),
    )

    # ----------------------------------------
    # 🔒 Blokada edycji po podpisaniu
    # ----------------------------------------

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.signed_by_client:
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    # ----------------------------------------
    # 🏢 Automatyczne przypisanie firmy
    # ----------------------------------------

    def save_model(self, request, obj, form, change):
        if not obj.company_id and hasattr(request.user, "company"):
            obj.company = request.user.company
        super().save_model(request, obj, form, change)


# =========================================================
# 🔹 PROTOKOL IMAGE ADMIN (opcjonalnie osobno)
# =========================================================

@admin.register(ProtokolImage)
class ProtokolImageAdmin(admin.ModelAdmin):
    list_display = ("protokol", "kind", "original_name", "uploaded_by", "uploaded_at")
    list_filter = ("kind", "uploaded_at")
    search_fields = ("original_name", "caption")
    readonly_fields = ("uploaded_by", "uploaded_at")


# =========================================================
# 🔹 PROTOKOL ACTIVITY ADMIN
# =========================================================

@admin.register(ProtocolActivity)
class ProtocolActivityAdmin(admin.ModelAdmin):
    list_display = ("protocol", "type", "title", "created_by", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("created_at",)