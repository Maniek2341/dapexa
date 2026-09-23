from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages

from app.rcp.models import TimeEntry
from app.rcp.utils import can_manage_own_time_entries


class TimeEntryDeleteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/rcp/timeentry_confirm_delete.html"

    def get_object(self, request, pk):
        return get_object_or_404(
            TimeEntry,
            pk=pk,
            company=request.user.company,
        )

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_own_time_entries(request.user):
            messages.error(request, "Nie możesz bezpośrednio usuwać wpisów. Wyślij prośbę o edycję.")
            return redirect("time_entry_list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        obj = self.get_object(request, pk)

        if obj.user != request.user:
            messages.error(request, "Możesz usuwać tylko swoje wpisy.")
            return redirect("time_entry_list")

        return render(request, self.template_name, {"object": obj})

    def post(self, request, pk):
        obj = self.get_object(request, pk)

        if obj.user != request.user:
            messages.error(request, "Możesz usuwać tylko swoje wpisy.")
            return redirect("time_entry_list")

        obj.delete()
        messages.success(request, "Wpis został usunięty.")
        return redirect("time_entry_list")