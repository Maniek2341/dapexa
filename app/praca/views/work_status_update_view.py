# app/praca/views/work_status_update_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.core.exceptions import PermissionDenied
from app.praca.permissions import has_work_permission

from app.praca.models import WorkOrder, WorkActivity


class WorkStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not has_work_permission(request.user, "work_status_update"):
            raise PermissionDenied
        work = get_object_or_404(
            WorkOrder,
            pk=pk,
            company=request.user.company,
        )

        status = request.POST.get("status")
        allowed = dict(WorkOrder.Status.choices)

        if (
            getattr(request.user, "role", None) == request.user.Role.EMPLOYEE
            and status not in {
                WorkOrder.Status.IN_PROGRESS,
            }
        ):
            raise PermissionDenied

        if (
            getattr(request.user, "role", None) == request.user.Role.PODWYKONAWCA
            and status == WorkOrder.Status.CANCELLED
        ):
            raise PermissionDenied("Podwykonawca nie może anulować pracy.")

        if status not in allowed:
            messages.error(request, "Nieprawidłowy status pracy.")
            return redirect("work_detail", pk=work.pk)

        old_status = work.status

        if old_status == WorkOrder.Status.DONE and status != WorkOrder.Status.DONE:
            messages.error(
                request,
                "Zakończona praca nie może zostać ponownie otwarta."
            )
            return redirect("work_detail", pk=work.pk)

        if old_status == status:
            messages.info(request, "Status pracy nie został zmieniony.")
            return redirect("work_detail", pk=work.pk)

        work.status = status
        work.save(update_fields=["status"])

        WorkActivity.objects.create(
            company=work.company,
            work=work,
            type=WorkActivity.Type.STATUS,
            title="Zmieniono status pracy",
            description=f"{allowed.get(old_status, old_status)} → {allowed[status]}",
            created_by=request.user,
        )

        messages.success(
            request,
            f"Status zmieniono: {allowed.get(old_status, old_status)} → {allowed[status]}."
        )
        return redirect("work_detail", pk=work.pk)
