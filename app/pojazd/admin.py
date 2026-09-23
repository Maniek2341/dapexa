# app/vehicles/admin.py
from django.contrib import admin
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "company", "brand", "model", "vin", "current_mileage", "is_active")
    search_fields = ("registration_number", "brand", "model", "vin")
    list_filter = ("company", "is_active")
    readonly_fields = ("created_at", "updated_at")
