from django.contrib import admin

from .models import SupportReply, SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "priority", "status", "created_by", "assigned_to", "created_at")
    list_filter = ("status", "priority", "module")
    search_fields = ("title", "description", "module")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SupportReply)
class SupportReplyAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "created_at")
    search_fields = ("content", "ticket__title")
    readonly_fields = ("created_at", "updated_at")
