from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View

from app.serwis.models import ServiceOrder
from app.serwis.models import ServiceActivity  # jeśli masz
from app.serwis.permissions import can_manage_services
from app.serwis.signals import log_service_activity  # jeśli masz


class SerwisDeleteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może usuwać serwisów.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        service = get_object_or_404(ServiceOrder, pk=pk, company=request.user.company)
        number = service.number
        title = service.title

        # activity (opcjonalnie) - zapis przed usunięciem
        try:
            log_service_activity(
                company=service.company,
                service=service,
                type=getattr(ServiceActivity.Type, "SYSTEM", "system"),
                title="Usunięto zgłoszenie",
                description=f"{number} – {title}",
                user=request.user,
            )
        except Exception:
            pass

        service.delete()
        messages.success(request, f"Serwis {number} został usunięty.")
        return HttpResponseRedirect(reverse_lazy("serwis_nowe"))
