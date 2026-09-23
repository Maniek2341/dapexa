from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View

from app.rcp.models import TimeEntryRequest, TimeEntryRequestStatus
from app.rcp.utils import can_manage_time_requests


class TimeEntryRequestApproveView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request, pk):
        if not can_manage_time_requests(request.user):
            messages.error(request, "Nie masz uprawnień do tej akcji.")
            return redirect("time_entry_request_list")

        obj = get_object_or_404(
            TimeEntryRequest,
            pk=pk,
            company=request.user.company,
        )

        if obj.status != TimeEntryRequestStatus.PENDING:
            messages.warning(request, "Ten wniosek został już rozpatrzony.")
            return redirect("time_entry_request_list")

        try:
            obj.approve(request.user)
            messages.success(request, "Wniosek został zatwierdzony.")
        except Exception as e:
            messages.error(request, f"Nie udało się zatwierdzić wniosku: {e}")

        return redirect("time_entry_request_list")