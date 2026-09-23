from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from app.core.models import PanelUser
from app.rcp.models import TimeEntryRequest, TimeEntryRequestStatus, TimeEntryRequestType
from app.rcp.forms import RejectTimeEntryRequestForm
from app.rcp.utils import can_manage_time_requests


class TimeEntryRequestListView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/rcp/request_list.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_time_requests(request.user):
            messages.error(request, "Nie masz dostępu do panelu wniosków.")
            return redirect("time_entry_list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        qs = TimeEntryRequest.objects.filter(
            company=request.user.company
        ).select_related(
            "user", "entry", "decided_by"
        ).order_by("-created_at")

        status = (request.GET.get("status") or "").strip()
        request_type = (request.GET.get("request_type") or "").strip()
        user_id = (request.GET.get("user") or "").strip()

        if status:
            qs = qs.filter(status=status)

        if request_type:
            qs = qs.filter(request_type=request_type)

        if user_id:
            qs = qs.filter(user_id=user_id)

        employees = PanelUser.objects.filter(
            company=request.user.company,
            is_active=True,
            is_active_employee=True,
        ).exclude(
            role=PanelUser.Role.CLIENT
        ).order_by("first_name", "last_name", "email")

        context = {
            "requests": qs,
            "employees": employees,
            "active_status": status,
            "active_request_type": request_type,
            "active_user_id": user_id,
            "status_choices": TimeEntryRequestStatus.choices,
            "type_choices": TimeEntryRequestType.choices,
            "reject_form": RejectTimeEntryRequestForm(),
        }
        return render(request, self.template_name, context)