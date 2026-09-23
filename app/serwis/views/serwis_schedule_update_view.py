from datetime import time
# app/serwis/views/serwis_schedule_update_view.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from app.serwis.models import ServiceOrder, ServiceActivity
from app.serwis.permissions import can_manage_services
from app.serwis.signals import log_service_activity  # jeśli masz
from app.core.models import CompanySettings

def _safe_next(request, fallback_url: str) -> str:
    nxt = (request.POST.get("next") or "").strip()
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return fallback_url

class SerwisScheduleUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może zmieniać terminu serwisu.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        service = get_object_or_404(ServiceOrder, pk=pk, company=request.user.company)

        start_raw = (request.POST.get("planned_start") or "").strip()
        end_raw = (request.POST.get("planned_end") or "").strip()

        start = parse_datetime(start_raw) if start_raw else None
        end = parse_datetime(end_raw) if end_raw else None

        settings = CompanySettings.objects.filter(
            company=request.user.company
        ).only("default_work_start_time", "default_work_end_time").first()
        workday_start = settings.default_work_start_time if settings else time(7, 0)
        workday_end = settings.default_work_end_time if settings else time(15, 0)
        for label, value in (("rozpoczęcia", start), ("zakończenia", end)):
            if value and not (workday_start <= value.time() <= workday_end):
                messages.error(request, f"Godzina {label} musi mieścić się w zakresie {workday_start:%H:%M}–{workday_end:%H:%M}.")
                return HttpResponseRedirect(reverse("serwis_detail", args=[service.pk]))

        if start and end and end < start:
            messages.error(request, "Data 'do' nie może być wcześniejsza niż 'od'.")
            return HttpResponseRedirect(reverse("serwis_detail", args=[service.pk]))

        service.planned_start = start
        service.planned_end = end
        service.save(update_fields=["planned_start", "planned_end"])

        desc = []

        auto_end = request.POST.get("auto_end") == "1"   # checkbox ma value="1"
        dur = (request.POST.get("duration_min") or "").strip()

        # ✅ tylko jeśli auto wyliczanie włączone
        if auto_end and dur:
            desc.append(f"Czas: {dur} min")

        desc.append(f"Od: {service.planned_start:%d.%m.%Y %H:%M}" if service.planned_start else "Od: —")
        desc.append(f"Do: {service.planned_end:%d.%m.%Y %H:%M}" if service.planned_end else "Do: —")
        desc = "\n".join(desc)

        try:
            log_service_activity(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.STATUS,  # albo Type.OTHER / Type.SYSTEM — jak wolisz
                title="Ustalono termin",
                description=desc,
                user=request.user,
            )
        except Exception:
            ServiceActivity.objects.create(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.SYSTEM,
                title="Ustalono termin",
                description=desc,
                created_by=request.user,
            )

        messages.success(request, "Zapisano termin serwisu.")
        fallback = reverse("serwis_detail", args=[service.pk])
        return redirect(_safe_next(request, fallback))
