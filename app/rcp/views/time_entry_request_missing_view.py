from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.core.mail import send_mail
from django.utils import timezone

from app.core.models import PanelUser
from app.rcp.forms import MissingHoursRequestForm
from app.rcp.models import TimeEntryRequest, TimeEntryRequestType


class TimeEntryRequestMissingView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != PanelUser.Role.EMPLOYEE:
            messages.info(request, "Ten formularz jest dostępny tylko dla pracownika.")
            return redirect("time_entry_list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect("time_entry_list")

    
    def post(self, request, *args, **kwargs):
        form = MissingHoursRequestForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Popraw dane formularza uzupełnienia zaległych godzin.")
            return redirect("time_entry_list")

        req_date = form.cleaned_data["date"]
        reason = form.cleaned_data["reason"]

        days_diff = (timezone.localdate() - req_date).days

        if days_diff < 0:
            messages.error(request, "Nie możesz wysłać prośby dla przyszłej daty.")
            return redirect("time_entry_list")

        if days_diff > 15:
            messages.error(request, "Możesz zgłosić zaległe godziny maksymalnie do 15 dni wstecz.")
            return redirect("time_entry_list")

        TimeEntryRequest.objects.create(
            company=request.user.company,
            user=request.user,
            request_type=TimeEntryRequestType.MISSING,
            date=req_date,
            new_start_time=request.POST.get("new_start_time") or "07:00",
            new_end_time=request.POST.get("new_end_time") or "15:00",
            reason=reason,
        )

        messages.success(request, "Prośba o uzupełnienie zaległych godzin została wysłana.")
        return redirect("time_entry_list")