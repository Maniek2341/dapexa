from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import LeaveType, LeaveAllowance, LeaveRequest, LeavePool


# =====================================================
# LEAVE TYPE
# =====================================================

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "company",
        "pool",
        "counts_against_limit",
        "annual_limit_days",
        "is_special",
    )

    list_filter = (
        "company",
        "pool",
        "counts_against_limit",
        "is_special",
    )

    search_fields = ("name", "code")
    ordering = ("company", "name")


# =====================================================
# LEAVE ALLOWANCE
# =====================================================

@admin.register(LeaveAllowance)
class LeaveAllowanceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "company",
        "year",
        "vacation_limit",
        "carryover_days",
        "adjustment_days",
        "total_available_display",
        "is_locked",
    )

    list_filter = (
        "company",
        "year",
        "is_locked",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
    )

    ordering = ("-year",)

    readonly_fields = (
        "total_available_display",
    )

    def total_available_display(self, obj):
        return obj.total_vacation_available()
    total_available_display.short_description = "Łącznie dostępne dni"


# =====================================================
# LEAVE REQUEST
# =====================================================

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "company",
        "leave_type",
        "date_from",
        "date_to",
        "days_count",
        "leave_year",
        "status_badge",
        "is_carryover",
        "approver",
    )

    list_filter = (
        "company",
        "status",
        "leave_type__pool",
        "leave_year",
        "is_carryover",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "reason",
    )

    ordering = ("-date_from",)

    readonly_fields = (
        "days_count",
        "approved_at",
    )

    actions = ["approve_requests", "reject_requests"]

    # ---------------------------------------
    # STATUS BADGE
    # ---------------------------------------

    def status_badge(self, obj):
        colors = {
            obj.Status.DRAFT: "gray",
            obj.Status.SUBMITTED: "orange",
            obj.Status.APPROVED: "green",
            obj.Status.REJECTED: "red",
            obj.Status.CANCELLED: "black",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = "Status"

    # ---------------------------------------
    # ACTIONS
    # ---------------------------------------

    def approve_requests(self, request, queryset):
        updated = queryset.update(
            status=LeaveRequest.Status.APPROVED,
            approver=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f"Zatwierdzono {updated} wniosków.")

    approve_requests.short_description = "Zatwierdź wybrane wnioski"

    def reject_requests(self, request, queryset):
        updated = queryset.update(
            status=LeaveRequest.Status.REJECTED,
            approver=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f"Odrzucono {updated} wniosków.")

    reject_requests.short_description = "Odrzuć wybrane wnioski"

    # ---------------------------------------
    # BLOKADA EDYCJI ZATWIERDZONYCH
    # ---------------------------------------

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == LeaveRequest.Status.APPROVED:
            return False
        return super().has_change_permission(request, obj)