from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.core.mail import send_mail

from app.core.models import PanelUser
from app.rcp.models import TimeEntry
from app.rcp.forms import SingleEntryEditRequestForm
from app.rcp.models import TimeEntryRequest, TimeEntryRequestType


class TimeEntryRequestEditSingleView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def get_object(self, request, pk):
        return get_object_or_404(
            TimeEntry,
            pk=pk,
            company=request.user.company,
            user=request.user,
        )

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != PanelUser.Role.EMPLOYEE:
            messages.info(request, "Ten formularz jest dostępny tylko dla pracownika.")
            return redirect("time_entry_list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect("time_entry_list")

    def post(self, request, pk, *args, **kwargs):
        entry = self.get_object(request, pk)
        form = SingleEntryEditRequestForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Popraw dane formularza prośby o edycję wpisu.")
            return redirect("time_entry_list")

        reason = form.cleaned_data["reason"]
        new_start = form.cleaned_data["new_start_time"]
        new_end = form.cleaned_data["new_end_time"]

        TimeEntryRequest.objects.create(
            company=request.user.company,
            user=request.user,
            request_type=TimeEntryRequestType.EDIT,
            entry=entry,
            date=entry.date,
            new_start_time=new_start,
            new_end_time=new_end,
            reason=reason,
        )

        messages.success(request, "Prośba o edycję wpisu została wysłana.")
        return redirect("time_entry_list")