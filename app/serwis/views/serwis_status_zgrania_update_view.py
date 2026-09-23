# views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views import View
from django.shortcuts import get_object_or_404, redirect

from app.serwis.models import ServiceOrder, ServiceActivity
from app.serwis.activity import log_service_activity
from app.serwis.permissions import can_manage_services


class SerwisStatusZgraniaUpdateView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może zmieniać statusu obsługi.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        service = get_object_or_404(
            ServiceOrder,
            pk=pk,
            company=request.user.company,
            status=ServiceOrder.Status.OBSLUGA,
        )
        next_url = request.POST.get("next") or "serwis_detail"

        new_status = (request.POST.get("status_zgrania") or "").strip()
        old_status = service.status_zgrania

        if new_status == old_status:
            return redirect(next_url, pk=pk)

        # ✅ czytelne nazwy: policz PRZED zapisem
        label_map = dict(ServiceOrder.StatusZgrania.choices)
        old_label = label_map.get(old_status, "—") if old_status else "—"
        new_label = label_map.get(new_status, new_status)

        desc = f"{old_label} → {new_label}"

        # zapisz
        service.status_zgrania = new_status
        service.save(update_fields=["status_zgrania"])

        try:
            log_service_activity(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.STATUS,
                title="Zmieniono status obsługi",
                description=desc,
                user=request.user,
            )
        except Exception:
            ServiceActivity.objects.create(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.SYSTEM,
                title="Zmieniono status obsługi",
                description=desc,
                created_by=request.user,
            )

        return redirect(next_url, pk=pk)
