from django.contrib import admin
from django.utils.html import format_html

from app.oferta_praca.models import (
    Offer,
    OfferNumberCounter,
    OfferVariant,
    OfferVariantItem,
    OfferVariantFile,
    OfferImage,
)


class OfferVariantFileInline(admin.TabularInline):
    model = OfferVariantFile
    extra = 0
    fields = ("title", "file", "file_link", "uploaded_at")
    readonly_fields = ("file_link", "uploaded_at")
    verbose_name = "Plik PDF"
    verbose_name_plural = "Pliki PDF"

    def file_link(self, obj):
        if obj.pk and obj.file:
            return format_html(
                '<a href="{}" target="_blank">Otwórz plik</a>',
                obj.file.url
            )
        return "—"
    file_link.short_description = "Podgląd"


class OfferVariantItemInline(admin.TabularInline):
    model = OfferVariantItem
    extra = 0
    fields = (
        "item_type",
        "product",
        "name",
        "quantity",
        "unit",
        "unit_price_netto",
        "vat_rate",
        "total_netto",
        "total_brutto",
    )
    readonly_fields = ("total_netto", "total_brutto")
    verbose_name = "Pozycja wariantu"
    verbose_name_plural = "Pozycje wariantu"


class OfferVariantInline(admin.StackedInline):
    model = OfferVariant
    extra = 0
    fields = (
        "source_type",
        "name",
        "description",
        "is_selected",
        "selected_at",
        "materials_netto",
        "accessories_netto",
        "labor_netto",
        "services_netto",
        "other_netto",
        "total_netto",
        "total_vat",
        "total_brutto",
    )
    readonly_fields = (
        "selected_at",
        "materials_netto",
        "accessories_netto",
        "labor_netto",
        "services_netto",
        "other_netto",
        "total_netto",
        "total_vat",
        "total_brutto",
    )
    show_change_link = True
    verbose_name = "Wariant"
    verbose_name_plural = "Warianty"


class OfferImageInline(admin.TabularInline):
    model = OfferImage
    extra = 0
    fields = ("file", "image_preview", "uploaded_at")
    readonly_fields = ("image_preview", "uploaded_at")
    verbose_name = "Zdjęcie"
    verbose_name_plural = "Zdjęcia"

    def image_preview(self, obj):
        if obj.pk and obj.file:
            return format_html(
                '<img src="{}" style="max-height:80px;border-radius:8px;" />',
                obj.file.url
            )
        return "—"
    image_preview.short_description = "Podgląd"


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "title",
        "client",
        "company",
        "status_badge",
        "priority_badge",
        "issue_date",
        "valid_until",
        "is_ordered",
        "approved_by_manager",
        "variants_count",
    )
    list_filter = (
        "status",
        "priority",
        "is_ordered",
        "approved_by_manager",
        "has_warranty",
        "has_service",
        "issue_date",
        "valid_until",
        "company",
    )
    search_fields = (
        "number",
        "title",
        "description",
        "notes",
        "order_number",
        "client__name",
        "location__name",
    )
    readonly_fields = (
        "number",
        "approved_at",
    )
    autocomplete_fields = (
        "client",
        "location",
        "approved_by",
        "assigned_employees",
    )
    inlines = [OfferVariantInline, OfferImageInline]

    fieldsets = (
        ("Podstawowe dane", {
            "fields": (
                "company",
                "number",
                "title",
                "client",
                "location",
                "status",
                "priority",
                "issue_date",
                "valid_until",
            )
        }),
        ("Zamówienie i realizacja", {
            "fields": (
                "order_number",
                "is_ordered",
                "order_date",
                "execution_date",
                "sent_to_client_at",
                "forwarded_to_execution_at",
            )
        }),
        ("Opis", {
            "fields": (
                "description",
                "notes",
            )
        }),
        ("Zespół i wykonanie", {
            "fields": (
                "assigned_employees",
                "employees_count",
                "labor_hours",
                "execution_days",
            )
        }),
        ("Dodatkowe opcje", {
            "fields": (
                "has_warranty",
                "has_service",
            )
        }),
        ("Zatwierdzenie", {
            "fields": (
                "approved_by_manager",
                "approved_by",
                "approved_at",
            )
        }),
    )

    actions = (
        "mark_as_approved",
        "mark_as_not_approved",
        "mark_as_sent",
        "mark_as_prepared",
    )

    def status_badge(self, obj):
        color_map = {
            Offer.STATUS_NOWE: "#6c757d",
            Offer.STATUS_SPOTKANIE: "#0dcaf0",
            Offer.STATUS_DOZROBIENIA: "#fd7e14",
            Offer.STATUS_PRZYGOTOWANE: "#0d6efd",
            Offer.STATUS_WYSLANE: "#198754",
            Offer.STATUS_NIEAKTUALNE: "#dc3545",
            Offer.STATUS_PRZEKAZANE: "#20c997",
        }
        return format_html(
            '<span style="padding:.28rem .55rem;border-radius:999px;color:#fff;background:{};">{}</span>',
            color_map.get(obj.status, "#6c757d"),
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def priority_badge(self, obj):
        color_map = {
            "low": "#6c757d",
            "normal": "#0d6efd",
            "high": "#fd7e14",
            "critical": "#dc3545",
        }
        return format_html(
            '<span style="padding:.28rem .55rem;border-radius:999px;color:#fff;background:{};">{}</span>',
            color_map.get(obj.priority, "#6c757d"),
            obj.get_priority_display(),
        )
    priority_badge.short_description = "Priorytet"

    def variants_count(self, obj):
        return obj.variants.count()
    variants_count.short_description = "Warianty"

    @admin.action(description="Oznacz jako zatwierdzone")
    def mark_as_approved(self, request, queryset):
        queryset.update(approved_by_manager=True)

    @admin.action(description="Cofnij zatwierdzenie")
    def mark_as_not_approved(self, request, queryset):
        queryset.update(approved_by_manager=False, approved_by=None, approved_at=None)

    @admin.action(description="Ustaw status: Wysłane")
    def mark_as_sent(self, request, queryset):
        queryset.update(status=Offer.STATUS_WYSLANE)

    @admin.action(description="Ustaw status: Przygotowane")
    def mark_as_prepared(self, request, queryset):
        queryset.update(status=Offer.STATUS_PRZYGOTOWANE)


@admin.register(OfferVariant)
class OfferVariantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "offer",
        "company",
        "source_type",
        "is_selected",
        "total_netto",
        "total_brutto",
        "items_count",
        "files_count",
    )
    list_filter = (
        "source_type",
        "is_selected",
        "company",
        "selected_at",
    )
    search_fields = (
        "name",
        "description",
        "offer__number",
        "offer__title",
        "offer__client__name",
    )
    readonly_fields = (
        "selected_at",
        "materials_netto",
        "accessories_netto",
        "labor_netto",
        "services_netto",
        "other_netto",
        "total_netto",
        "total_vat",
        "total_brutto",
    )
    autocomplete_fields = ("offer",)
    inlines = [OfferVariantItemInline, OfferVariantFileInline]

    fieldsets = (
        ("Podstawowe dane", {
            "fields": (
                "company",
                "offer",
                "source_type",
                "name",
                "description",
                "is_selected",
                "selected_at",
            )
        }),
        ("Podsumowanie kosztów", {
            "fields": (
                "materials_netto",
                "accessories_netto",
                "labor_netto",
                "services_netto",
                "other_netto",
                "total_netto",
                "total_vat",
                "total_brutto",
            )
        }),
    )

    actions = ("mark_selected", "mark_unselected", "recalculate_selected_variants")

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = "Pozycje"

    def files_count(self, obj):
        return obj.files.count()
    files_count.short_description = "Pliki"

    @admin.action(description="Oznacz jako wybrane")
    def mark_selected(self, request, queryset):
        for obj in queryset:
            obj.is_selected = True
            obj.save(update_fields=["is_selected", "selected_at"])

    @admin.action(description="Odznacz warianty")
    def mark_unselected(self, request, queryset):
        for obj in queryset:
            obj.is_selected = False
            obj.save(update_fields=["is_selected", "selected_at"])

    @admin.action(description="Przelicz sumy wariantów")
    def recalculate_selected_variants(self, request, queryset):
        for obj in queryset:
            obj.recalculate_totals()


@admin.register(OfferVariantItem)
class OfferVariantItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "variant",
        "item_type",
        "product",
        "quantity",
        "unit",
        "unit_price_netto",
        "total_netto",
        "total_brutto",
        "company",
    )
    list_filter = (
        "item_type",
        "company",
        "vat_rate",
    )
    search_fields = (
        "name",
        "variant__name",
        "variant__offer__number",
        "variant__offer__title",
        "product__name",
        "product__sku",
    )
    autocomplete_fields = ("variant", "product")
    readonly_fields = ("total_netto", "vat_value", "total_brutto")

    fieldsets = (
        ("Podstawowe dane", {
            "fields": (
                "company",
                "variant",
                "item_type",
                "product",
                "name",
            )
        }),
        ("Ilości i ceny", {
            "fields": (
                "quantity",
                "unit",
                "unit_price_netto",
                "vat_rate",
                "total_netto",
                "vat_value",
                "total_brutto",
            )
        }),
    )


@admin.register(OfferVariantFile)
class OfferVariantFileAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "variant",
        "company",
        "uploaded_at",
        "file_link",
    )
    list_filter = (
        "uploaded_at",
        "company",
    )
    search_fields = (
        "title",
        "variant__name",
        "variant__offer__number",
        "variant__offer__title",
    )
    autocomplete_fields = ("variant",)
    readonly_fields = ("uploaded_at", "file_link")

    fieldsets = (
        ("Plik", {
            "fields": (
                "company",
                "variant",
                "title",
                "file",
                "file_link",
                "uploaded_at",
            )
        }),
    )

    def file_link(self, obj):
        if obj.pk and obj.file:
            return format_html(
                '<a href="{}" target="_blank">Otwórz PDF</a>',
                obj.file.url
            )
        return "—"
    file_link.short_description = "Podgląd"


@admin.register(OfferImage)
class OfferImageAdmin(admin.ModelAdmin):
    list_display = (
        "offer",
        "company",
        "uploaded_at",
        "image_preview",
    )
    list_filter = (
        "uploaded_at",
        "company",
    )
    search_fields = (
        "offer__number",
        "offer__title",
        "offer__client__name",
    )
    autocomplete_fields = ("offer",)
    readonly_fields = ("uploaded_at", "image_preview")

    fieldsets = (
        ("Zdjęcie", {
            "fields": (
                "company",
                "offer",
                "file",
                "image_preview",
                "uploaded_at",
            )
        }),
    )

    def image_preview(self, obj):
        if obj.pk and obj.file:
            return format_html(
                '<img src="{}" style="max-height:100px;border-radius:10px;" />',
                obj.file.url
            )
        return "—"
    image_preview.short_description = "Podgląd"


@admin.register(OfferNumberCounter)
class OfferNumberCounterAdmin(admin.ModelAdmin):
    list_display = ("company", "year", "last_number")
    list_filter = ("year", "company")
    search_fields = ("company__name",)