from django.db import models
from app.core.models import CompanyOwnedModel, PanelUser
from app.core.view_permissions import view_permissions
from django.conf import settings
from django.utils import timezone


class Task(CompanyOwnedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Otwarte"
        IN_PROGRESS = "in_progress", "W trakcie"
        DONE = "done", "Zrobione"

    class AssignmentType(models.TextChoices):
        USER = "user", "Jedna osoba"
        ROLE = "role", "Rola"
        ALL = "all", "Dla wszystkich"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    assignment_type = models.CharField(
        max_length=20,
        choices=AssignmentType.choices,
        default=AssignmentType.USER
    )

    # 1) jedna konkretna osoba
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_assigned",
        help_text="Używane tylko przy 'Jedna osoba'"
    )

    # 2) czynnik roli
    assigned_role = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=PanelUser.Role.choices,
        help_text="Używane tylko przy 'Rola'"
    )

    # kto utworzył
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_created"
    )

    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return (
            self.due_date is not None
            and self.due_date < timezone.localdate()
            and self.status != self.Status.DONE
        )

    # --- Logika przypisania ---

    def is_assigned_to_user(self, user: PanelUser):
        """Sprawdza, czy dany user powinien widzieć zadanie."""
        if self.assignment_type == self.AssignmentType.ALL:
            return True

        if self.assignment_type == self.AssignmentType.USER:
            return self.assigned_user_id == user.id

        if self.assignment_type == self.AssignmentType.ROLE:
            return self.assigned_role == user.role

        return False
    
    class Meta:
        verbose_name = 'Zadanie'
        verbose_name_plural = 'Zadania'
        permissions = view_permissions(
            "task_list", "task_create", "task_delete", "task_complete",
        )
