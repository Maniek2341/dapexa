from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from app.core.models import PanelUser, CompanySettings
from app.serwis.forms import ServiceNoteForm
from app.serwis.models import ServiceActivity, ServiceNote, ServiceOrder
from app.serwis.permissions import can_manage_services


class SerwisDetailView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')
    template_name = "app/serwis/detail.html"

    def get(self, request, pk):
        service = get_object_or_404(
            ServiceOrder.objects
            .select_related("client")
            .prefetch_related("assigned_to", "media"),
            pk=pk,
            company=request.user.company,  # 🔒 tylko własna firma
        )

        notes = (
            ServiceNote.objects
            .filter(company=request.user.company, service=service)
            .select_related("author")
            .order_by("-is_pinned", "-created_at")
        )

        client = service.client

        activities = (
            ServiceActivity.objects
            .filter(company=request.user.company, service=service)
            .select_related("created_by")
            .order_by("-created_at")
        )

        work_logs = service.work_logs.select_related("worker").order_by("-work_date", "-created_at")

        today = timezone.localdate()

        context = {
            "service": service,
            "client": client,
            "notes": notes,
            "note_form": ServiceNoteForm(),
            "activities": activities,
            "work_logs": work_logs,
            "can_add_work_log": request.user.has_perm("serwis.access_service_work_log_add"),
            "activities_count": activities.count(),
            "today_key": today.strftime("%Y-%m-%d"),
            "yesterday_key": (today - timezone.timedelta(days=1)).strftime("%Y-%m-%d"),
            "can_manage_services": can_manage_services(request.user),
            "can_create_protocol_from_service": request.user.has_perm(
                "protokol.access_protocol_from_service"
            ),
            'contact_people': client.contacts.all(),
            'workers': PanelUser.objects.filter(company=request.user.company, is_active=True).order_by("first_name", "last_name")
        }
        company_settings = CompanySettings.objects.filter(company=request.user.company).only("default_work_start_time", "default_work_end_time").first()
        context["workday_start_time"] = company_settings.default_work_start_time.strftime("%H:%M") if company_settings else "07:00"
        context["workday_end_time"] = company_settings.default_work_end_time.strftime("%H:%M") if company_settings else "15:00"
        context["can_service_quick_actions"] = (
            context["can_create_protocol_from_service"]
            or (
                service.settlement_method == ServiceOrder.SettlementMethod.HOURLY
                and context["can_add_work_log"]
            )
        )


        return render(request, self.template_name, context)
