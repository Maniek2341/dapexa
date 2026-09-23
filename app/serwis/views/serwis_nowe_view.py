from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q

from app.core.models import PanelUser
from app.core.models import CompanySettings
from app.serwis.models import ServiceOrder
from app.serwis.permissions import can_manage_services


class SerwisNoweView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/serwis/nowe.html"

    def get(self, request):
        status = request.GET.get("status", "new")
        q = request.GET.get("q", "").strip()

        qs = (
            ServiceOrder.objects
            .filter(company=request.user.company)
            .select_related("client")
            .prefetch_related("assigned_to")
            .order_by("-id")
        )

        if status == "new":
            qs = qs.filter(
                status__in=[
                    ServiceOrder.Status.NEW,
                    ServiceOrder.Status.IN_PROGRESS,
                ]
            )
            active = "new"

        elif status == "forgoted":
            qs = qs.filter(status=ServiceOrder.Status.FORGOTED)
            active = "forgoted"

        elif status == "obsluga":
            qs = qs.filter(status=ServiceOrder.Status.OBSLUGA)
            active = "obsluga"

        elif status == "done":
            qs = qs.filter(status=ServiceOrder.Status.DONE)
            active = "done"

        else:
            active = "all"

        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(number__icontains=q) |
                Q(client__name__icontains=q) |
                Q(client__first_name__icontains=q) |
                Q(client__last_name__icontains=q) |
                Q(status__icontains=q) |
                Q(status_zgrania__icontains=q)
            ).distinct()

        workers = (
            PanelUser.objects
            .filter(company=request.user.company, is_active=True)
            .order_by("first_name", "last_name")
        )

        context = {
            "services": qs,
            "active_status": active,
            "workers": workers,
            "q": q,
            "can_manage_services": can_manage_services(request.user),
            "new_count": ServiceOrder.objects.filter(
                company=request.user.company,
                status__in=[
                    ServiceOrder.Status.NEW,
                    ServiceOrder.Status.IN_PROGRESS,
                ],
            ).count(),
            "obsluga_count": ServiceOrder.objects.filter(
                company=request.user.company,
                status=ServiceOrder.Status.OBSLUGA,
            ).count(),
        }
        company_settings = CompanySettings.objects.filter(
            company=request.user.company
        ).only("default_work_start_time", "default_work_end_time").first()
        context["workday_start_time"] = company_settings.default_work_start_time.strftime("%H:%M") if company_settings else "07:00"
        context["workday_end_time"] = company_settings.default_work_end_time.strftime("%H:%M") if company_settings else "15:00"

        return render(request, self.template_name, context)
