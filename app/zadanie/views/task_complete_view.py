from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.zadanie.models import Task


class TaskCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if getattr(request.user, "role", None) == request.user.Role.PODWYKONAWCA:
            raise PermissionDenied("Podwykonawca nie ma dostępu do modułu zadań.")
        task = get_object_or_404(
            Task,
            pk=pk,
            company=request.user.company,
        )

        if not task.is_assigned_to_user(request.user):
            raise PermissionDenied("Nie możesz oznaczyć tego zadania jako wykonanego.")

        if task.status != Task.Status.DONE:
            task.status = Task.Status.DONE
            task.save(update_fields=["status", "updated_at"])
            messages.success(request, "Zadanie zostało oznaczone jako wykonane.")
        else:
            messages.info(request, "Zadanie było już oznaczone jako wykonane.")

        return redirect(request.META.get("HTTP_REFERER", "dashboard"))
