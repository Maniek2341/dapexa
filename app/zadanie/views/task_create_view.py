from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView

from app.zadanie.models import Task
from app.zadanie.forms import TaskForm
from app.core.models import PanelUser
from app.core.notifications import notify_assigned_users


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "app/zadanie/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        task = form.save(commit=False)
        task.company = self.request.user.company
        task.created_by = self.request.user
        if not task.title.strip():
            task.title = task.description.strip().splitlines()[0][:255] if task.description.strip() else "Nowe zadanie"
        task.save()

        if task.assignment_type == Task.AssignmentType.USER:
            assignees = [task.assigned_user] if task.assigned_user_id else []
        elif task.assignment_type == Task.AssignmentType.ROLE:
            assignees = PanelUser.objects.filter(
                company=task.company,
                role=task.assigned_role,
                is_active=True,
                is_active_employee=True,
            )
        else:
            assignees = PanelUser.objects.filter(
                company=task.company,
                is_active=True,
                is_active_employee=True,
            ).exclude(role__in=[PanelUser.Role.CLIENT, PanelUser.Role.PODWYKONAWCA])
        notify_assigned_users(
            company=task.company,
            users=assignees,
            subject=f"Przypisano Ci zadanie: {task.title}",
            message=(
                f"Przypisano Ci zadanie: {task.title}.\n"
                f"Termin: {task.due_date or 'nieustalony'}\n"
                f"Opis: {task.description or '—'}"
            ),
        )

        messages.success(self.request, "Zadanie zostało dodane.")
        return redirect("task_list")
