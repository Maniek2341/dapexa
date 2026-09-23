# app/leaves/models.py
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from app.core.models import CompanyOwnedModel
from app.core.view_permissions import view_permissions
from django.core.validators import MinValueValidator
import holidays

# app/leaves/models.py
from django.db import models
from django.conf import settings
from app.core.models import CompanyOwnedModel


class LeavePool(models.TextChoices):
    VACATION = "vacation", "Wypoczynkowy"
    CARE = "care", "Opiekuńczy"
    OTHER = "other", "Inne / nielimitowane"


class LeaveType(CompanyOwnedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)

    pool = models.CharField(max_length=20, choices=LeavePool.choices, default=LeavePool.OTHER)

    counts_against_limit = models.BooleanField(default=True)
    annual_limit_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # dla wyjątków (np. "na żądanie"=4)

    is_special = models.BooleanField(default=False)  # macierzyński/rodzicielski itp.

    def __str__(self):
        return self.name

class LeaveAllowance(CompanyOwnedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_allowances")
    year = models.PositiveIntegerField()

    # Podstawowa pula wypoczynkowego na rok (20/26 lub proporcjonalnie)
    vacation_limit = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])

    # Zaległy przeniesiony (z roku-1), też schodzi przy wypoczynkowym
    carryover_days = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Ręczne korekty HR (np. +2, -1)
    adjustment_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # “Na żądanie” – sublimit (zwykle 4), ale schodzi z vacation (czyli tylko ograniczenie ilości)
    on_demand_limit = models.DecimalField(max_digits=5, decimal_places=2, default=4, validators=[MinValueValidator(0)])

    # Termin wykorzystania zaległego (PL często: 30 września)
    carryover_deadline = models.DateField(null=True, blank=True)

    is_locked = models.BooleanField(default=False)  # blokada edycji przez automaty (np. po zamknięciu roku)

    class Meta:
        unique_together = (("company", "user", "year"),)
        ordering = ["-year", "user_id"]

    def __str__(self):
        return f"{self.user} {self.year} (vac:{self.vacation_limit}, carry:{self.carryover_days})"

    # Dostępny limit ogólny (wypoczynkowy + zaległy + korekty)
    def total_vacation_available(self):
        return (self.vacation_limit or 0) + (self.carryover_days or 0) + (self.adjustment_days or 0)

class LeaveRequest(CompanyOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Szkic"
        SUBMITTED = "submitted", "Wysłany"
        APPROVED = "approved", "Zatwierdzony"
        REJECTED = "rejected", "Odrzucony"
        CANCELLED = "cancelled", "Anulowany"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)

    date_from = models.DateField()
    date_to = models.DateField()
    days_count = models.DecimalField(max_digits=5, decimal_places=2, editable=False)

    # rok rozliczeniowy i czy zaległy
    leave_year = models.PositiveIntegerField(default=timezone.now().year)
    is_carryover = models.BooleanField(default=False)

    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="approved_leaves"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError("Data zakończenia nie może być wcześniejsza niż rozpoczęcia.")

    
    def calculate_working_days(self):
        if not self.date_from or not self.date_to:
            return Decimal("0")

        pl_holidays = holidays.Poland()

        current = self.date_from
        working_days = 0

        while current <= self.date_to:
            if current.weekday() < 5 and current not in pl_holidays:
                working_days += 1
            current += timedelta(days=1)

        return Decimal(working_days)

    def save(self, *args, **kwargs):
        self.full_clean()
        self.days_count = self.calculate_working_days()
        super().save(*args, **kwargs)

    class Meta:
        permissions = view_permissions(
            "urlop_add", "leave_type_add", "leave_type_edit",
            "leave_type_delete", "leave_type_list", "leave_allowance_list",
            "generate_leave_allowances", "hr_leave_list", "hr_leave_approve",
            "hr_leave_reject", "hr_leave_cancel", "hr_leave_pdf",
        )
