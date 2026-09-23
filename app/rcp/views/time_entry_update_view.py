from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages

from app.rcp.models import TimeEntry
from app.rcp.forms import TimeEntryForm
from app.rcp.utils import can_manage_own_time_entries


class TimeEntryUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/rcp/timeentry_form.html"

    def get_object(self, request, pk):
        return get_object_or_404(
            TimeEntry,
            pk=pk,
            company=request.user.company,
        )

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_own_time_entries(request.user):
            messages.error(request, "Nie możesz bezpośrednio edytować wpisów. Wyślij prośbę o edycję.")
            return redirect("time_entry_list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        obj = self.get_object(request, pk)

        if obj.user != request.user:
            messages.error(request, "Możesz edytować tylko swoje wpisy.")
            return redirect("time_entry_list")

        form = TimeEntryForm(instance=obj)
        return render(request, self.template_name, {
            "form": form,
            "object": obj,
            "page_title": "Edycja wpisu RCP",
            "submit_label": "Edytuj wpis",
        })

    def post(self, request, pk):
        obj = self.get_object(request, pk)

        if obj.user != request.user:
            messages.error(request, "Możesz edytować tylko swoje wpisy.")
            return redirect("time_entry_list")

        form = TimeEntryForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Wpis został zaktualizowany.")
            return redirect("time_entry_list")

        messages.error(request, "Popraw błędy w formularzu.")
        return render(request, self.template_name, {
            "form": form,
            "object": obj,
            "page_title": "Edycja wpisu RCP",
            "submit_label": "Edytuj wpis",
        })