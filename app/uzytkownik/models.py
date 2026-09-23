from django.contrib.auth.models import Group
import uuid

from django.db import models
from django.db.models import Q

from app.core.fields import TrackedFileField, file_size_field
from app.core.models import Company, PanelUser


def employee_training_certificate_path(instance, filename):
    return "Firmy/{0}/pracownicy/{1}/szkolenia/{2}".format(
        instance.company_id or "firma",
        instance.employee_id or "pracownik",
        filename,
    )


def employee_contract_file_path(instance, filename):
    return "Firmy/{0}/pracownicy/{1}/umowy/{2}".format(
        instance.company_id or "firma",
        instance.employee_id or "pracownik",
        filename,
    )


class CompanyRoleGroup(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="role_permission_groups",
    )
    group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        related_name="company_role_group",
    )
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=PanelUser.Role.choices)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_role_group_name_per_company",
            ),
            models.UniqueConstraint(
                fields=["company", "role"],
                condition=Q(is_system=True),
                name="unique_system_role_group_per_company",
            ),
        ]
        verbose_name = "Grupa uprawnień roli"
        verbose_name_plural = "Grupy uprawnień ról"

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"


class OwnershipTransfer(models.Model):
    class Status(models.TextChoices):
        OWNER_PENDING = "owner_pending", "Oczekuje na obecnego właściciela"
        RECIPIENT_PENDING = "recipient_pending", "Oczekuje na przyszłego właściciela"
        CONFIRMED = "confirmed", "Potwierdzony"
        CANCELLED = "cancelled", "Anulowany"
        EXPIRED = "expired", "Wygasł"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="ownership_transfers",
    )
    current_owner = models.ForeignKey(
        PanelUser,
        on_delete=models.CASCADE,
        related_name="initiated_ownership_transfers",
    )
    new_owner = models.ForeignKey(
        PanelUser,
        on_delete=models.CASCADE,
        related_name="received_ownership_transfers",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OWNER_PENDING,
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                condition=Q(
                    status__in=["owner_pending", "recipient_pending"]
                ),
                name="unique_pending_ownership_transfer_per_company",
            ),
        ]
        verbose_name = "Przekazanie właściciela"
        verbose_name_plural = "Przekazania właściciela"

    def __str__(self):
        return f"{self.company}: {self.current_owner} → {self.new_owner}"


class EmployeeTraining(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="employee_trainings",
    )
    employee = models.ForeignKey(
        PanelUser,
        on_delete=models.CASCADE,
        related_name="trainings",
    )
    name = models.CharField(max_length=180, verbose_name="Nazwa szkolenia")
    organizer = models.CharField(
        max_length=180,
        blank=True,
        verbose_name="Organizator",
    )
    completed_at = models.DateField(verbose_name="Data ukończenia")
    valid_until = models.DateField(
        null=True,
        blank=True,
        verbose_name="Ważne do",
    )
    certificate_number = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Numer certyfikatu",
    )
    certificate_image = TrackedFileField(
        blank=True,
        null=True,
        upload_to=employee_training_certificate_path,
        max_length=500,
        verbose_name="Zdjęcie certyfikatu",
    )
    certificate_image_size = file_size_field("Rozmiar zdjęcia certyfikatu")
    notes = models.TextField(blank=True, verbose_name="Notatki")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-completed_at", "-created_at"]
        verbose_name = "Szkolenie pracownika"
        verbose_name_plural = "Szkolenia pracowników"

    def __str__(self):
        return f"{self.employee} — {self.name}"

    @property
    def is_expired(self):
        from django.utils import timezone

        return bool(self.valid_until and self.valid_until < timezone.localdate())


class EmployeeContract(models.Model):
    class ContractType(models.TextChoices):
        EMPLOYMENT = "employment", "Umowa o pracę"
        MANDATE = "mandate", "Umowa zlecenie"
        SPECIFIC_WORK = "specific_work", "Umowa o dzieło"
        B2B = "b2b", "Kontrakt B2B"
        OTHER = "other", "Inna"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="employee_contracts",
    )
    employee = models.ForeignKey(
        PanelUser,
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    contract_type = models.CharField(
        max_length=30,
        choices=ContractType.choices,
        default=ContractType.EMPLOYMENT,
        verbose_name="Rodzaj umowy",
    )
    date_from = models.DateField(verbose_name="Data od")
    date_to = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data do",
    )
    contract_image = TrackedFileField(
        blank=True,
        null=True,
        upload_to=employee_contract_file_path,
        max_length=500,
        verbose_name="Zdjęcie umowy",
    )
    contract_image_size = file_size_field("Rozmiar zdjęcia umowy")
    notes = models.TextField(blank=True, verbose_name="Notatki")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_from", "-created_at"]
        verbose_name = "Umowa pracownika"
        verbose_name_plural = "Umowy pracowników"

    def __str__(self):
        return f"{self.employee} — {self.get_contract_type_display()} od {self.date_from}"

    @property
    def is_finished(self):
        from django.utils import timezone

        return bool(self.date_to and self.date_to < timezone.localdate())
