from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from app.zadanie.models import Task


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "app/zadanie/task_list.html"
    context_object_name = "tasks"

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, "role", None) == request.user.Role.PODWYKONAWCA:
            raise PermissionDenied("Podwykonawca nie ma dostępu do modułu zadań.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "all").strip()

        tasks = (
            Task.objects
            .filter(company=user.company)
            .select_related("assigned_user", "created_by")
        )

        if q:
            tasks = tasks.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(assigned_user__first_name__icontains=q) |
                Q(assigned_user__last_name__icontains=q) |
                Q(assigned_user__email__icontains=q)
            )

        if status and status != "all":
            tasks = tasks.filter(status=status)

        return tasks.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["q"] = self.request.GET.get("q", "").strip()
        context["active_status"] = self.request.GET.get("status", "all").strip() or "all"

        return context
