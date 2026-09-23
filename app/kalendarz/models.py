# app/calendar_app/models.py
from django.db import models
from app.core.models import CompanyOwnedModel
from django.conf import settings


class Event(CompanyOwnedModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
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
