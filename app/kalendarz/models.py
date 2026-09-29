# app/calendar_app/models.py
from django.db import models
from app.core.models import CompanyOwnedModel
from django.conf import settings


class Event(CompanyOwnedModel):
    class Recurrence(models.TextChoices):
        NONE = "none", "Bez powtarzania"
        DAILY = "daily", "Codziennie (dni robocze)"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    recurrence = models.CharField(
        max_length=10,
        choices=Recurrence.choices,
        default=Recurrence.NONE,
    )
    recurrence_until = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_calendar_events",
    )
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="calendar_events"
    )
    related_service = models.ForeignKey(
        "serwis.ServiceOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_events"
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Kalendarz'
        verbose_name_plural = 'Kalendarz'
