# app/rcp/models.py
from datetime import datetime, date as pydate
from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

from app.core.models import CompanyOwnedModel
from app.core.view_permissions import view_permissions


class WorkMode(models.TextChoices):
    OFFICE = "office", "Stacjonarna"
    REMOTE = "remote", "Zdalna"
    FIELD = "field", "Teren"
    DELEGACJA = "delegacja", "Delegacja"


class TimeEntryStatus(models.TextChoices):
    DRAFT = "draft", "Roboczy"
    SUBMITTED = "submitted", "Wysłany"
    APPROVED = "approved", "Zatwierdzony"
    REJECTED = "rejected", "Odrzucony"


class TimeEntry(CompanyOwnedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
    )

    date = models.DateField("Data", db_index=True)

    start_time = models.TimeField("Godzina od")
    end_time = models.TimeField("Godzina do")

    break_minutes = models.PositiveIntegerField("Przerwa (min)", default=0)

    work_mode = models.CharField(
        "Tryb pracy",
        max_length=20,
        choices=WorkMode.choices,
        default=WorkMode.OFFICE,
    )

    status = models.CharField(
        "Status",
        max_length=20,
        choices=TimeEntryStatus.choices,
        default=TimeEntryStatus.APPROVED,
        db_index=True,
    )

    description = models.TextField("Opis pracy", blank=True)

    requires_explanation = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_time_entries",
    )
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_time_entries",
    )

    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rejestracja czasu pracy"
        verbose_name_plural = "Rejestracja czasu pracy"
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "user", "date"],
                name="unique_time_entry_per_user_per_day",
            )
        ]
        indexes = [
            models.Index(fields=["company", "user", "date"]),
            models.Index(fields=["company", "status", "date"]),
        ]
        permissions = view_permissions(
            "time_entry_create", "time_entry_list", "time_entry_update",
            "time_entry_delete", "time_entry_request_edit",
            "time_entry_request_missing", "time_entry_request_edit_single",
            "time_entry_request_approve", "time_entry_request_reject",
            "time_entry_request_list", "time_entry_pdf",
        )

    def __str__(self):
        return f"{self.user} - {self.date} ({self.start_time}-{self.end_time})"

    def clean(self):
        super().clean()

        if self.user_id and self.company_id and getattr(self.user, "company_id", None) != self.company_id:
            raise ValidationError("Użytkownik należy do innej firmy.")

        start_dt = datetime.combine(pydate.today(), self.start_time)
        end_dt = datetime.combine(pydate.today(), self.end_time)

        if end_dt <= start_dt:
            raise ValidationError({
                "end_time": "Godzina zakończenia musi być późniejsza niż godzina rozpoczęcia."
            })

        total_minutes = int((end_dt - start_dt).total_seconds() // 60)

        if self.break_minutes > total_minutes:
            raise ValidationError({
                "break_minutes": "Przerwa nie może być dłuższa niż cały czas pracy."
            })

        if total_minutes > 12 * 60:
            self.requires_explanation = True

    @property
    def duration_minutes(self):
        start_dt = datetime.combine(pydate.today(), self.start_time)
        end_dt = datetime.combine(pydate.today(), self.end_time)
        total_minutes = int((end_dt - start_dt).total_seconds() // 60)
        return max(total_minutes - self.break_minutes, 0)

    @property
    def duration_hours(self):
        return (Decimal(self.duration_minutes) / Decimal("60")).quantize(Decimal("0.01"))



class TimeEntryRequestType(models.TextChoices):
    MISSING = "missing", "Uzupełnienie brakujących godzin"
    EDIT = "edit", "Edycja godzin"


class TimeEntryRequestStatus(models.TextChoices):
    PENDING = "pending", "Oczekujący"
    APPROVED = "approved", "Zatwierdzony"
    REJECTED = "rejected", "Odrzucony"


class TimeEntryRequest(CompanyOwnedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entry_requests",
    )

    request_type = models.CharField(
        "Typ wniosku",
        max_length=20,
        choices=TimeEntryRequestType.choices,
    )

    entry = models.ForeignKey(
        TimeEntry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="requests",
    )

    date = models.DateField("Data", null=True, blank=True)

    new_start_time = models.TimeField("Nowa godzina od", null=True, blank=True)
    new_end_time = models.TimeField("Nowa godzina do", null=True, blank=True)

    reason = models.TextField("Powód")

    status = models.CharField(
        "Status",
        max_length=20,
        choices=TimeEntryRequestStatus.choices,
        default=TimeEntryRequestStatus.PENDING,
        db_index=True,
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_time_entry_requests",
    )
    decided_at = models.DateTimeField("Data decyzji", null=True, blank=True)
    rejection_reason = models.TextField("Powód odrzucenia", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Wniosek RCP"
        verbose_name_plural = "Wnioski RCP"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "user"]),
            models.Index(fields=["company", "request_type"]),
        ]

    def __str__(self):
        return f"{self.get_request_type_display()} - {self.user} - {self.get_status_display()}"

    def clean(self):
        super().clean()

        if self.user_id and self.company_id and getattr(self.user, "company_id", None) != self.company_id:
            raise ValidationError("Użytkownik należy do innej firmy.")

        if self.request_type == TimeEntryRequestType.EDIT and not self.entry_id:
            raise ValidationError({"entry": "Dla wniosku o edycję musisz wskazać wpis."})

        if self.request_type == TimeEntryRequestType.MISSING and not self.date:
            raise ValidationError({"date": "Dla brakujących godzin musisz wskazać datę."})

        if self.new_start_time and self.new_end_time and self.new_end_time <= self.new_start_time:
            raise ValidationError({
                "new_end_time": "Godzina zakończenia musi być późniejsza niż rozpoczęcia."
            })

    def approve(self, decided_by):
        self.status = TimeEntryRequestStatus.APPROVED
        self.decided_by = decided_by
        self.decided_at = timezone.now()
        self.rejection_reason = ""

        if self.request_type == TimeEntryRequestType.MISSING:
            TimeEntry.objects.create(
                company=self.company,
                user=self.user,
                date=self.date,
                start_time=self.new_start_time,
                end_time=self.new_end_time,
                work_mode=WorkMode.OFFICE,
                status=TimeEntryStatus.APPROVED,
                submitted_at=timezone.now(),
                approved_at=timezone.now(),
                approved_by=decided_by,
            )

        elif self.request_type == TimeEntryRequestType.EDIT and self.entry:
            self.entry.start_time = self.new_start_time
            self.entry.end_time = self.new_end_time
            self.entry.status = TimeEntryStatus.APPROVED
            self.entry.approved_at = timezone.now()
            self.entry.approved_by = decided_by
            self.entry.rejected_at = None
            self.entry.rejected_by = None
            self.entry.rejection_reason = ""
            self.entry.save()

        self.save()

    def reject(self, decided_by, reason=""):
        self.status = TimeEntryRequestStatus.REJECTED
        self.decided_by = decided_by
        self.decided_at = timezone.now()
        self.rejection_reason = reason
        self.save()
