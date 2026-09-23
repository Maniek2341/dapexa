from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    PanelUser,
    Company,
    CompanySettings,
    Address,
    Subscription,
    RouteDistanceCache,
)


# =====================================================
# ADDRESS
# =====================================================

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("street", "street_no", "postcode", "city", "country", "latitude", "longitude")
    search_fields = ("street", "postcode", "city")
    readonly_fields = ("latitude", "longitude")
    list_filter = ("city", "country")


# =====================================================
# COMPANY SETTINGS INLINE
# =====================================================

class CompanySettingsInline(admin.StackedInline):
    model = CompanySettings
    can_delete = False
    extra = 0


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = (
        "company", "default_vat",
        "default_work_start_time", "default_work_end_time",
        "notification_email", "updated_at",
    )
    search_fields = ("company__name", "notification_email")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Firma", {"fields": ("company",)}),
        ("Koszty i stawki", {"fields": (
            "travel_cost_per_km", "labor_price_1_worker",
            "labor_price_2_workers", "labor_price_3_workers",
            "default_vat",
        )}),
        ("RCP", {"fields": ("default_work_start_time", "default_work_end_time")}),
        ("Numeracja", {"fields": (
            "default_protocol_valid_days", "protocol_number_prefix",
            "protocol_number_digits", "service_number_prefix", "service_number_digits",
        )}),
        ("Powiadomienia", {"fields": ("notification_email", "notification_modules")}),
        ("Daty", {"fields": ("created_at", "updated_at")}),
    )


# =====================================================
# COMPANY
# =====================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "nip", "email", "phone", "is_active", "created_at")
    search_fields = ("name", "nip", "email")
    list_filter = ("is_active",)
    inlines = [CompanySettingsInline]


# =====================================================
# PANEL USER
# =====================================================

@admin.register(PanelUser)
class PanelUserAdmin(UserAdmin):
    model = PanelUser

    list_display = (
        "email",
        "company",
        "role",
        "is_admin",
        "is_active_employee",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "role",
        "is_admin",
        "is_active",
        "company",
    )

    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)

    readonly_fields = (
        "date_joined", "last_login", "avatar_size",
        "login_2fa_code_hash", "login_2fa_expires_at",
        "login_2fa_attempts", "created_at", "updated_at",
    )

    fieldsets = (
        ("Dane logowania", {
            "fields": ("email", "password")
        }),
        ("Dane osobowe", {
            "fields": (
                "first_name",
                "last_name",
                "phone",
                "phone_priv",
                "birthday",
                "gender",
                "avatar",
                "avatar_size",
            )
        }),
        ("Firma i rola", {
            "fields": (
                "company",
                "role",
                "position",
                "is_admin",
                "is_staff",
                "is_superuser",
                "two_factor_enabled",
            )
        }),
        ("Zatrudnienie", {
            "fields": (
                "employment_start_date",
                "previous_employment_years",
                "employment_fraction",
                "is_active_employee",
            )
        }),
        ("Uprawnienia systemowe", {
            "fields": (
                "is_active",
                "groups",
                "user_permissions",
                "email_notification_modules",
            )
        }),
        ("Daty", {
            "fields": (
                "date_joined", "last_login", "created_at", "updated_at",
                "login_2fa_code_hash", "login_2fa_expires_at", "login_2fa_attempts",
            )
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "company", "role"),
        }),
    )


# =====================================================
# SUBSCRIPTION
# =====================================================

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "package",
        "billing_period",
        "extra_users",
        "status",
        "is_trial_badge",
        "trial_days_left_display",
        "current_period_end",
    )

    list_filter = (
        "package",
        "billing_period",
        "status",
    )

    search_fields = (
        "company__name",
        "stripe_customer_id",
        "stripe_subscription_id",
        "stripe_extra_user_item_id",
    )

    readonly_fields = (
        "stripe_customer_id",
        "stripe_subscription_id",
        "current_period_start",
        "current_period_end",
        "created_at",
        "updated_at",
    )

    def is_trial_badge(self, obj):
        if obj.is_trial:
            return obj.is_trial
        return "-"
    is_trial_badge.short_description = "Trial"

    def trial_days_left_display(self, obj):
        if obj.is_trial:
            return obj.trial_days_left
        return "-"
    trial_days_left_display.short_description = "Dni triala"


# =====================================================
# ROUTE DISTANCE CACHE
# =====================================================

@admin.register(RouteDistanceCache)
class RouteDistanceCacheAdmin(admin.ModelAdmin):
    list_display = (
        "origin_lat",
        "origin_lng",
        "dest_lat",
        "dest_lng",
        "distance_km",
        "created_at",
    )

    readonly_fields = (
        "origin_lat",
        "origin_lng",
        "dest_lat",
        "dest_lng",
        "distance_km",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
