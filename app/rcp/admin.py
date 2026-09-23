# app/rcp/admin.py
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    TimeEntry,
    TimeEntryRequest,
    TimeEntryStatus,
    TimeEntryRequestStatus,
)


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "company",
        "date",
        "start_time",
        "end_time",
        "break_minutes",
        "work_mode",
        "status",
        "duration_hours_display",
        "requires_explanation",
        "approved_by",
        "approved_at",
        "created_at",
    )
    list_filter = (
        "company",
        "status",
        "work_mode",
        "requires_explanation",
        "date",
        "created_at",
        "approved_at",
        "rejected_at",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "description",
        "rejection_reason",
    )
    readonly_fields = (
        "submitted_at",
        "approved_at",
        "rejected_at",
        "created_at",
        "updated_at",
        "duration_minutes_display",
        "duration_hours_display",
    )
    autocomplete_fields = (
        "company",
        "user",
        "approved_by",
        "rejected_by",
    )
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")

    fieldsets = (
        ("Podstawowe informacje", {
            "fields": (
                "company",
                "user",
                "date",
                "work_mode",
                "status",
            )
        }),
        ("Godziny pracy", {
            "fields": (
                ("start_time", "end_time"),
                "break_minutes",
                "description",
                "requires_explanation",
            )
        }),
        ("Podsumowanie", {
            "fields": (
                "duration_minutes_display",
                "duration_hours_display",
            )
        }),
        ("Akceptacja / odrzucenie", {
            "fields": (
                "submitted_at",
                ("approved_at", "approved_by"),
                ("rejected_at", "rejected_by"),
                "rejection_reason",
            )
        }),
        ("System", {
            "classes": ("collapse",),
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def duration_minutes_display(self, obj):
        return obj.duration_minutes
    duration_minutes_display.short_description = "Czas pracy (min)"

    def duration_hours_display(self, obj):
        return obj.duration_hours
    duration_hours_display.short_description = "Czas pracy (h)"

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "company",
            "user",
            "approved_by",
            "rejected_by",
        )
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "company") and request.user.company_id:
            return qs.filter(company=request.user.company)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request.user, "company") and request.user.company_id:
            if db_field.name == "company":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    id=request.user.company_id
                )
            elif db_field.name in {"user", "approved_by", "rejected_by"}:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    company=request.user.company
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.company_id and hasattr(request.user, "company") and request.user.company_id:
            obj.company = request.user.company

        try:
            obj.full_clean()
        except ValidationError as e:
            form.add_error(None, e)
            return

        super().save_model(request, obj, form, change)


@admin.register(TimeEntryRequest)
class TimeEntryRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "company",
        "request_type",
        "status",
        "date",
        "entry",
        "new_start_time",
        "new_end_time",
        "decided_by",
        "decided_at",
        "created_at",
    )
    list_filter = (
        "company",
        "request_type",
        "status",
        "created_at",
        "decided_at",
        "date",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "reason",
        "rejection_reason",
    )
    readonly_fields = (
        "created_at",
        "decided_at",
    )
    autocomplete_fields = (
        "company",
        "user",
        "entry",
        "decided_by",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ("approve_requests", "reject_requests")

    fieldsets = (
        ("Podstawowe informacje", {
            "fields": (
                "company",
                "user",
                "request_type",
                "status",
            )
        }),
        ("Dane wniosku", {
            "fields": (
                "entry",
                "date",
                ("new_start_time", "new_end_time"),
                "reason",
            )
        }),
        ("Decyzja", {
            "fields": (
                ("decided_by", "decided_at"),
                "rejection_reason",
            )
        }),
        ("System", {
            "classes": ("collapse",),
            "fields": (
                "created_at",
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "company",
            "user",
            "entry",
            "decided_by",
        )
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "company") and request.user.company_id:
            return qs.filter(company=request.user.company)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request.user, "company") and request.user.company_id:
            if db_field.name == "company":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    id=request.user.company_id
                )
            elif db_field.name in {"user", "decided_by"}:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    company=request.user.company
                )
            elif db_field.name == "entry":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    company=request.user.company
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.company_id and hasattr(request.user, "company") and request.user.company_id:
            obj.company = request.user.company

        try:
            obj.full_clean()
        except ValidationError as e:
            form.add_error(None, e)
            return

        super().save_model(request, obj, form, change)

    @admin.action(description="Zatwierdź wybrane wnioski")
    def approve_requests(self, request, queryset):
        approved_count = 0

        for obj in queryset:
            if obj.status != TimeEntryRequestStatus.PENDING:
                continue
            try:
                obj.approve(decided_by=request.user)
                approved_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Nie udało się zatwierdzić wniosku ID {obj.id}: {e}",
                    level=messages.ERROR,
                )

        if approved_count:
            self.message_user(
                request,
                f"Zatwierdzono {approved_count} wniosków.",
                level=messages.SUCCESS,
            )

    @admin.action(description="Odrzuć wybrane wnioski")
    def reject_requests(self, request, queryset):
        rejected_count = 0

        for obj in queryset:
            if obj.status != TimeEntryRequestStatus.PENDING:
                continue
            try:
                obj.reject(
                    decided_by=request.user,
                    reason="Odrzucono z poziomu panelu administratora.",
                )
                rejected_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Nie udało się odrzucić wniosku ID {obj.id}: {e}",
                    level=messages.ERROR,
                )

        if rejected_count:
            self.message_user(
                request,
                f"Odrzucono {rejected_count} wniosków.",
                level=messages.WARNING,
            )