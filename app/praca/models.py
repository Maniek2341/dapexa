from django.db import models
from django.conf import settings
from app.core.models import CompanyOwnedModel
from app.core.view_permissions import view_permissions
from django.utils import timezone
from django.db import transaction

class WorkOrderNumberCounter(models.Model):
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("company", "year")

class WorkOrder(CompanyOwnedModel):
    class Status(models.TextChoices):
        NEW = "new", "Nowe"
        IN_PROGRESS = "in_progress", "W realizacji"
        DONE = "done", "Zakończone"
        CANCELLED = "cancelled", "Anulowane"

    offer = models.OneToOneField(
        "oferta_praca.Offer",
        on_delete=models.PROTECT,
        related_name="work_order",
        verbose_name="Oferta",
    )

    client = models.ForeignKey(
        "klient.Client",
        on_delete=models.PROTECT,
        related_name="work_orders",
        verbose_name="Klient",
    )

    location = models.ForeignKey(
        "klient.ClientLocation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_orders",
        verbose_name="Lokalizacja",
    )

    number = models.CharField(max_length=50, verbose_name="Numer pracy")
    title = models.CharField(max_length=255, verbose_name="Tytuł")
    description = models.TextField(blank=True, verbose_name="Opis")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name="Status",
    )

    order_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Numer zamówienia",
    )
    is_ordered = models.BooleanField(default=False, verbose_name="Czy zamówiono")

    planned_start = models.DateTimeField(null=True, blank=True, verbose_name="Planowana data rozpoczęcia")
    planned_end = models.DateTimeField(null=True, blank=True, verbose_name="Planowana data zakończenia")

    employees_count = models.PositiveIntegerField(default=0, verbose_name="Ilu pracowników")
    labor_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Roboczogodziny")
    execution_days = models.PositiveIntegerField(default=0, verbose_name="Dni na wykonanie")

    assigned_employees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_work_orders",
        verbose_name="Przypisani pracownicy",
    )

    total_netto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_brutto = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_work_orders",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Praca"
        verbose_name_plural = "Prace"
        permissions = view_permissions(
            "workorder_list", "work_detail", "work_assign_workers",
            "work_schedule_update", "work_mark_ordered", "work_status_update",
            "work_finish",
        )

    def __str__(self):
        return f"{self.number} - {self.title}"

    @classmethod
    def generate_number(cls, company):
        year = timezone.now().year
        with transaction.atomic():
            counter, _ = WorkOrderNumberCounter.objects.select_for_update().get_or_create(
                company=company,
                year=year,
                defaults={"last_number": 0},
            )
            counter.last_number += 1
            counter.save(update_fields=["last_number"])
        return f"PR/{year}/{counter.last_number:04d}"


class WorkActivity(CompanyOwnedModel):
    class Type(models.TextChoices):
        SYSTEM = "system", "System"
        STATUS = "status", "Zmiana statusu"
        SCHEDULE = "schedule", "Termin"
        WORKERS = "workers", "Pracownicy"
        ORDER = "order", "Zamówienie sprzętu"
        NOTE = "note", "Notatka"

    work = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="Praca",
    )

    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM,
        verbose_name="Typ",
    )

    title = models.CharField(max_length=255, verbose_name="Tytuł")
    description = models.TextField(blank=True, verbose_name="Opis")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_activities",
        verbose_name="Użytkownik",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data")

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Historia pracy"
        verbose_name_plural = "Historia prac"

    def save(self, *args, **kwargs):
        if self.work_id and not self.company_id:
            self.company = self.work.company
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.work.number} / {self.title}"
