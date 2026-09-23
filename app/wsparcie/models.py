from django.conf import settings
from django.db import models

from app.core.models import CompanyOwnedModel
from app.core.view_permissions import view_permissions


class SupportTicket(CompanyOwnedModel):
    class Status(models.TextChoices):
        NEW = "new", "Nowe"
        IN_PROGRESS = "in_progress", "W trakcie"
        WAITING = "waiting", "Oczekuje na informacje"
        RESOLVED = "resolved", "Rozwiązane"

    class Priority(models.TextChoices):
        LOW = "low", "Niski"
        NORMAL = "normal", "Normalny"
        HIGH = "high", "Wysoki"
        URGENT = "urgent", "Pilny"

    title = models.CharField(max_length=200)
    description = models.TextField()
    module = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="support_tickets_created")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="support_tickets_assigned")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Zgłoszenie wsparcia"
        verbose_name_plural = "Zgłoszenia wsparcia"
        permissions = view_permissions(
            "support_list", "support_create", "support_detail", "support_update", "support_reply", "support_status_update",
        )

    def __str__(self):
        return self.title


class SupportReply(CompanyOwnedModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    content = models.TextField()

    class Meta:
        ordering = ["created_at"]
