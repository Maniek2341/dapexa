from datetime import time
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View
from django.core.exceptions import PermissionDenied
from app.praca.permissions import has_work_permission

from app.praca.models import WorkOrder, WorkActivity
from app.core.models import CompanySettings


class WorkScheduleUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not has_work_permission(request.user, "work_schedule_update"):
            raise PermissionDenied
        work = get_object_or_404(
            WorkOrder,
            pk=pk,
            company=request.user.company,
        )

        old_start = work.planned_start
        old_end = work.planned_end

        planned_start_raw = request.POST.get("planned_start") or ""
        planned_end_raw = request.POST.get("planned_end") or ""

        planned_start = parse_datetime(planned_start_raw) if planned_start_raw else None
        planned_end = parse_datetime(planned_end_raw) if planned_end_raw else None

        if planned_start_raw and planned_start is None:
            messages.error(request, "Nieprawidłowa data rozpoczęcia.")
            return redirect("workorder_list")

        if planned_end_raw and planned_end is None:
            messages.error(request, "Nieprawidłowa data zakończenia.")
            return redirect("workorder_list")

        if planned_start and timezone.is_naive(planned_start):
            planned_start = timezone.make_aware(
                planned_start,
                timezone.get_current_timezone()
            )

        if planned_end and timezone.is_naive(planned_end):
            planned_end = timezone.make_aware(
                planned_end,
                timezone.get_current_timezone()
            )

        settings = CompanySettings.objects.filter(
            company=request.user.company
        ).only("default_work_start_time", "default_work_end_time").first()
        workday_start = settings.default_work_start_time if settings else time(7, 0)
        workday_end = settings.default_work_end_time if settings else time(15, 0)
        for label, value in (("rozpoczęcia", planned_start), ("zakończenia", planned_end)):
            if value and not (workday_start <= value.timetz().replace(tzinfo=None) <= workday_end):
                messages.error(request, f"Godzina {label} musi mieścić się w zakresie {workday_start:%H:%M}–{workday_end:%H:%M}.")
                return redirect("workorder_list")

        if planned_start and planned_end and planned_end < planned_start:
            messages.error(request, "Data zakończenia nie może być wcześniejsza niż rozpoczęcia.")
            return redirect("workorder_list")

        work.planned_start = planned_start
        work.planned_end = planned_end
        work.save(update_fields=["planned_start", "planned_end"])

        WorkActivity.objects.create(
            company=work.company,
            work=work,
            type=WorkActivity.Type.SCHEDULE,
            title="Zmieniono termin pracy",
            description=(
                f"Start: {old_start or '—'} → {planned_start or '—'}\n"
                f"Koniec: {old_end or '—'} → {planned_end or '—'}"
            ),
            created_by=request.user,
        )

        messages.success(request, "Termin pracy został zaktualizowany.")
        return redirect("workorder_list")
