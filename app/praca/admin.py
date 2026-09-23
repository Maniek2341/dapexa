# app/warehouse/admin.py
from django.contrib import admin
from .models import WorkOrder


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "title",
        "client",
        "status",
        "planned_start",
        "planned_end",
        "employees_count",
        "labor_hours",
    )
    list_filter = ("company", "status", "planned_start", "planned_end")
    search_fields = ("number", "title", "description", "client__name")
    readonly_fields = ("created_at",)
    filter_horizontal = ("assigned_employees",)
