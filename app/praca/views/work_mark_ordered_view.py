from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.core.exceptions import PermissionDenied
from app.praca.permissions import has_work_permission

from app.praca.models import WorkOrder, WorkActivity


class WorkMarkOrderedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not has_work_permission(request.user, "work_mark_ordered"):
            raise PermissionDenied
        work = get_object_or_404(
            WorkOrder,
            pk=pk,
            company=request.user.company,
        )

        old_order_number = work.order_number
        was_ordered = work.is_ordered

        order_number = (request.POST.get("order_number") or "").strip()

        if not order_number:
            messages.error(request, "Podaj numer zamówienia.")
            return redirect("work_detail", pk=work.pk)

        work.is_ordered = True
        work.order_number = order_number
        work.save(update_fields=["is_ordered", "order_number"])

        if was_ordered:
            description = f"Zmieniono numer zamówienia: {old_order_number or '—'} → {order_number}"
        else:
            description = f"Oznaczono sprzęt jako zamówiony. Numer zamówienia: {order_number}"

        WorkActivity.objects.create(
            company=work.company,
            work=work,
            type=WorkActivity.Type.ORDER,
            title="Zamówiono sprzęt",
            description=description,
            created_by=request.user,
        )

        messages.success(request, "Oznaczono, że sprzęt został zamówiony.")
        return redirect("work_detail", pk=work.pk)
