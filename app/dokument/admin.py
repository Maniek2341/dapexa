# app/documents/admin.py
from django.contrib import admin
from .models import DocumentFolder, Document


@admin.register(DocumentFolder)
class DocumentFolderAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "parent")
    search_fields = ("name",)
    list_filter = ("company",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "folder", "uploaded_by", "created_at")
    search_fields = ("name", "folder__name", "uploaded_by__username")
    list_filter = ("company", "folder")
    readonly_fields = ("created_at", "updated_at")