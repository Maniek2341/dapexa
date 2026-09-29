# app/praca/views/work_actions.py

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.dateparse import parse_date
from django.views import View
from django.core.exceptions import PermissionDenied
from app.praca.permissions import has_work_permission

from app.praca.models import WorkOrder, WorkActivity
from app.core.notifications import notify_assigned_users

User = get_user_model()


class WorkAssignWorkersView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not has_work_permission(request.user, "work_assign_workers"):
            raise PermissionDenied
        work = get_object_or_404(
            WorkOrder,
            pk=pk,
            company=request.user.company,
        )

        old_workers = list(work.assigned_employees.all())

        workers_ids = request.POST.getlist("workers")

        workers = list(
            User.objects.filter(
                pk__in=workers_ids,
                company=request.user.company,
                is_active=True,
            )[:3]
        )

        work.assigned_employees.set(workers)
        old_worker_ids = {worker.pk for worker in old_workers}
        newly_assigned = [worker for worker in workers if worker.pk not in old_worker_ids]
        notify_assigned_users(
            company=work.company,
            users=newly_assigned,
            subject=f"Przypisano Cię do pracy {work.number}",
            message=(
                f"Przypisano Cię do pracy {work.number}: {work.title}.\n"
                f"Oferta: {work.offer or '—'}\n"
                f"Termin: {work.planned_start or 'nieustalony'}"
            ),
        )
        work.employees_count = len(workers)
        work.save(update_fields=["employees_count"])

        old_names = ", ".join(
            w.get_full_name() or w.email for w in old_workers
        ) or "Brak"

        new_names = ", ".join(
            w.get_full_name() or w.email for w in workers
        ) or "Brak"

        WorkActivity.objects.create(
            company=work.company,
            work=work,
            type=WorkActivity.Type.WORKERS,
            title="Zmieniono pracowników",
            description=f"{old_names} → {new_names}",
            created_by=request.user,
        )

        messages.success(request, "Pracownicy zostali przypisani do pracy.")
        return redirect("work_detail", pk=work.pk)
