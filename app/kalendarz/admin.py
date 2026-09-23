# app/calendar_app/admin.py
from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "start", "end", "related_service")
    search_fields = ("title", "related_service__number")
    list_filter = ("company", "start", "end")
    filter_horizontal = ("attendees",)
    readonly_fields = ("created_at", "updated_at")
