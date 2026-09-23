from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View

from app.rcp.models import TimeEntryRequest, TimeEntryRequestStatus
from app.rcp.forms import RejectTimeEntryRequestForm
from app.rcp.utils import can_manage_time_requests


class TimeEntryRequestRejectView(LoginRequiredMixin, View):
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

        form = RejectTimeEntryRequestForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Podaj powód odrzucenia.")
            return redirect("time_entry_request_list")

        obj.reject(
            decided_by=request.user,
            reason=form.cleaned_data["reason"],
        )
        messages.success(request, "Wniosek został odrzucony.")
        return redirect("time_entry_request_list")