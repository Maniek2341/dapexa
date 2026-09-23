from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.core.exceptions import PermissionDenied
from app.praca.permissions import has_work_permission

from app.praca.models import WorkOrder, WorkActivity
from app.protokoly.models import Protocol


class WorkFinishView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not has_work_permission(request.user, "work_finish"):
            raise PermissionDenied
        work = get_object_or_404(
            WorkOrder,
            pk=pk,
            company=request.user.company,
        )

        if work.status == WorkOrder.Status.DONE:
            messages.info(request, "Ta praca jest już zakończona.")
            return redirect("work_detail", pk=work.pk)

        description = (request.POST.get("description") or "").strip()

        if not description:
            messages.error(request, "Uzupełnij opis wykonanych prac.")
            return redirect("work_detail", pk=work.pk)

        protocol = Protocol.objects.create(
            company=work.company,
            client=work.client,
            status=Protocol.Status.NEW,
            description=description,
            travel_cost_net=Decimal(request.POST.get("travel_cost_net") or "0"),
            labor_cost_net=Decimal(request.POST.get("labor_cost_net") or "0"),
            materials_cost_net=Decimal(request.POST.get("materials_cost_net") or "0"),
            invoice_notes=request.POST.get("invoice_notes", "").strip(),
        )

        work.status = WorkOrder.Status.DONE
        work.save(update_fields=["status"])

        WorkActivity.objects.create(
            company=work.company,
            work=work,
            type=WorkActivity.Type.STATUS,
            title="Zakończono pracę",
            description=f"Utworzono protokół: {protocol}",
            created_by=request.user,
        )

        messages.success(request, "Praca została zakończona i utworzono protokół.")
        return redirect("work_detail", pk=work.pk)
