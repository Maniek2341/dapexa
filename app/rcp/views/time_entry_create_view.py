from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View

from app.rcp.forms import TimeEntryForm
from app.rcp.models import TimeEntry, TimeEntryStatus

class TimeEntryCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/rcp/timeentry_form.html"

    def get(self, request):
        form = TimeEntryForm(request=request)
        return render(request, self.template_name, {
            "form": form,
            "page_title": "Nowy wpis RCP",
            "submit_label": "Zapisz wpis",
        })

    def post(self, request):
        form = TimeEntryForm(request.POST, request=request)
        if form.is_valid():
            try:
                entry = form.save()
                messages.success(request, "Wpis RCP został zapisany.")
                return redirect("time_entry_list")
            except Exception as e:
                form.add_error(None, str(e))

        return render(request, self.template_name, {
            "form": form,
            "page_title": "Nowy wpis RCP",
            "submit_label": "Zapisz wpis",
        })
