from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import View

from app.serwis.models import ServiceOrder, ServiceActivity
from app.serwis.permissions import can_manage_services
from app.serwis.signals import log_service_activity


class SerwisPriorityUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może zmieniać priorytetu serwisu.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        service = get_object_or_404(ServiceOrder, pk=pk, company=request.user.company)

        next_url = (request.POST.get("next") or "").strip() or reverse_lazy("serwis_detail", args=[service.pk])
        new_priority = (request.POST.get("priority") or "").strip()

        allowed = {"critical", "high", "normal", "low"}
        if new_priority not in allowed:
            messages.error(request, "Nieprawidłowy priorytet.")
            return HttpResponseRedirect(next_url)

        old_priority = service.priority
        if old_priority == new_priority:
            messages.info(request, "Priorytet bez zmian.")
            return HttpResponseRedirect(next_url)

        service.priority = new_priority
        service.save(update_fields=["priority"])

        old_label = service.__class__.Priority(old_priority).label if old_priority else "—"
        new_label = service.__class__.Priority(new_priority).label

        desc = f"Zmieniono priorytet: {old_label} → {new_label}"

        try:
            log_service_activity(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.STATUS,
                title="Zmieniono priorytet",
                description=desc,
                user=request.user,
            )
        except Exception:
            ServiceActivity.objects.create(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.SYSTEM,
                title="Zmieniono priorytet",
                description=desc,
                created_by=request.user,
            )

        messages.success(request, "Zapisano priorytet.")
        return HttpResponseRedirect(next_url)
