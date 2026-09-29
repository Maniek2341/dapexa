from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils import timezone

from .models import LeaveAllowance, LeavePool, LeaveRequest, LeaveType
from .services import decide_leave_request


class CompanyScopedAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        if not request.user.company_id:
            return queryset.none()
        return queryset.filter(company_id=request.user.company_id)

    def get_exclude(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_exclude(request, obj)
        return tuple(set(super().get_exclude(request, obj) or ()) | {"company"})

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.company_id = request.user.company_id
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and request.user.company_id:
            if db_field.name == "user":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(company_id=request.user.company_id)
            if db_field.name in {"leave_type", "approver"}:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(company_id=request.user.company_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(LeaveType)
class LeaveTypeAdmin(CompanyScopedAdmin):
    list_display = ("name", "code", "company", "pool", "counts_against_limit", "annual_limit_days", "is_special")
    list_filter = ("company", "pool", "counts_against_limit", "is_special")
    search_fields = ("name", "code")
    ordering = ("company", "name")


@admin.register(LeaveAllowance)
class LeaveAllowanceAdmin(CompanyScopedAdmin):
    list_display = ("user", "company", "year", "vacation_limit", "carryover_days", "adjustment_days", "total_available_display", "is_locked")
    list_filter = ("company", "year", "is_locked")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    ordering = ("-year",)
    readonly_fields = ("total_available_display",)

    @admin.display(description="Łącznie dostępne dni")
    def total_available_display(self, obj):
        return obj.total_vacation_available()


@admin.register(LeaveRequest)
class LeaveRequestAdmin(CompanyScopedAdmin):
    list_display = ("user", "company", "leave_type", "date_from", "date_to", "days_count", "leave_year", "status", "is_carryover", "approver")
    list_filter = ("company", "status", "leave_type__pool", "leave_year", "is_carryover")
    search_fields = ("user__email", "user__first_name", "user__last_name", "reason")
    ordering = ("-date_from",)
    readonly_fields = ("days_count", "approved_at", "status", "approver")
    actions = ("approve_requests", "reject_requests")

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == LeaveRequest.Status.APPROVED:
            return False
        return super().has_delete_permission(request, obj)

    @admin.action(description="Zatwierdź wybrane oczekujące wnioski")
    def approve_requests(self, request, queryset):
        self._decide_requests(request, queryset, LeaveRequest.Status.APPROVED)

    @admin.action(description="Odrzuć wybrane oczekujące wnioski")
    def reject_requests(self, request, queryset):
        self._decide_requests(request, queryset, LeaveRequest.Status.REJECTED)

    def _decide_requests(self, request, queryset, decision):
        if not request.user.is_superuser and request.user.role not in {"owner", "manager", "biuro"}:
            self.message_user(request, "Brak uprawnień do decyzji HR.", level=messages.ERROR)
            return
        done = 0
        errors = []
        records = queryset.select_related("company").values_list("pk", "company_id")
        for leave_id, company_id in records:
            try:
                company = request.user.company if not request.user.is_superuser else None
                if company is None:
                    from app.core.models import Company
                    company = Company.objects.get(pk=company_id)
                decide_leave_request(company, request.user, leave_id, decision)
                done += 1
            except (LeaveRequest.DoesNotExist, ValueError, ValidationError) as exc:
                errors.append(str(exc))
        self.message_user(request, f"Rozpatrzono {done} wniosków.")
        for error in errors[:5]:
            self.message_user(request, error, level=messages.ERROR)
