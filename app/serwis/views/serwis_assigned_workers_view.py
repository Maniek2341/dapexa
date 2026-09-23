from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from app.serwis.models import ServiceOrder, ServiceActivity
from app.serwis.permissions import can_manage_services
from app.serwis.signals import log_service_activity
from app.core.models import PanelUser

def _safe_next(request, fallback_url: str) -> str:
    nxt = (request.POST.get("next") or "").strip()
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return fallback_url

class SerwisAssignWorkersView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może przypisywać osób do serwisu.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        service = get_object_or_404(ServiceOrder, pk=pk, company=request.user.company)

        # --- stare (do loga) ---
        old_workers = list(service.assigned_to.all())
        old_names = ", ".join(f"{u.first_name} {u.last_name}" for u in old_workers) or "Brak"

        # --- nowe ---
        worker_ids = request.POST.getlist("workers")

        # zachowaj kolejność z formularza + limit 3
        worker_ids = [str(x) for x in worker_ids if str(x).strip()]
        worker_ids = worker_ids[:3]

        # pobierz i ułóż w tej samej kolejności co worker_ids
        qs = PanelUser.objects.filter(company=request.user.company, id__in=worker_ids)
        by_id = {str(u.id): u for u in qs}
        workers = [by_id[i] for i in worker_ids if i in by_id]  # kolejność z POST

        service.assigned_to.set(workers)  # ✅ zapisuje też usunięcia

        new_names = ", ".join(f"{u.first_name} {u.last_name}" for u in workers) or "Brak"

        desc = f"Z: {old_names}\nNa: {new_names}"

        try:
            log_service_activity(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.STATUS,
                title="Zmieniono serwisantów",
                description=desc,
                user=request.user,
            )
        except Exception:
            ServiceActivity.objects.create(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.STATUS,
                title="Zmieniono serwisantów",
                description=desc,
                created_by=request.user,
            )

        messages.success(request, "Zapisano serwisantów.")
        fallback = reverse("serwis_detail", args=[service.pk])
        return redirect(_safe_next(request, fallback))
