from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.utils import timezone

from app.core.models import PanelUser
from app.serwis.forms import ServiceWorkLogForm
from app.serwis.models import ServiceOrder, ServiceWorkLog


class ServiceWorkLogCreateView(LoginRequiredMixin, View):
    template_name = "app/serwis/work_log_add.html"
    login_url = reverse_lazy("login")

    def get_service(self, request, pk):
        return get_object_or_404(ServiceOrder, pk=pk, company=request.user.company)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm("serwis.access_service_work_log_add"):
            raise PermissionDenied("Nie masz uprawnień do dodawania dziennych wpisów serwisu.")
        service = self.get_service(request, kwargs["pk"])
        if service.settlement_method != ServiceOrder.SettlementMethod.HOURLY:
            raise PermissionDenied("Ten serwis jest rozliczany od roboty.")
        if request.user.role == PanelUser.Role.EMPLOYEE and not service.assigned_to.filter(pk=request.user.pk).exists():
            raise PermissionDenied("Możesz wpisywać czas tylko do przypisanego serwisu.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        service = self.get_service(request, pk)
        form = ServiceWorkLogForm(user=request.user, service=service)
        return render(request, self.template_name, {"form": form, "service": service})

    def post(self, request, pk):
        service = self.get_service(request, pk)
        form = ServiceWorkLogForm(request.POST, user=request.user, service=service)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.company = request.user.company
            entry.service = service
            entry.worker = request.user
            entry.save()
            messages.success(request, "Dzienny wpis serwisu został zapisany.")
            return redirect("serwis_detail", service.pk)
        return render(request, self.template_name, {"form": form, "service": service})
