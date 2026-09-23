from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from app.urlop.forms import LeaveRequestForm
from app.urlop.models import LeaveRequest
from app.urlop.services import (
    get_remaining_days,
    get_leave_limits_for_user,
)


class LeaveRequestCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/urlop/urlop_add.html"

    permission_required = "urlop.access_urlop_add"

    def dispatch(self, request, *args, **kwargs):
        # Składanie wniosku jest dostępne tylko użytkownikom posiadającym
        # dedykowane uprawnienie (w tym domyślnie pracownikom).
        if not request.user.has_perm(self.permission_required):
            raise PermissionDenied("Nie masz uprawnień do składania wniosków urlopowych.")
        return super().dispatch(request, *args, **kwargs)

    def _build_context(self, request, form):
        year = timezone.now().year

        remaining_days = get_remaining_days(
            request.user.company,
            request.user,
            year,
        )

        leave_limits = get_leave_limits_for_user(
            request.user.company,
            request.user,
            year,
        )

        leave_limits_map = {
            str(item["leave_type"].id): {
                "name": item["leave_type"].name,
                "limit": str(item["limit"]),
                "used": str(item["used"]),
                "remaining": str(item["remaining"]),
            }
            for item in leave_limits
        }

        return {
            "form": form,
            "remaining_days": remaining_days,
            "leave_limits": leave_limits,
            "leave_limits_map": leave_limits_map,
        }

    def get(self, request, *args, **kwargs):
        form = LeaveRequestForm(user=request.user)
        context = self._build_context(request, form)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = LeaveRequestForm(request.POST, user=request.user)

        if form.is_valid():
            leave = form.save(commit=False)
            leave.company = request.user.company
            leave.user = request.user
            leave.days_count = form.cleaned_data["days_count_calc"]
            leave.leave_year = form.cleaned_data["leave_year"]
            leave.is_carryover = form.cleaned_data.get("is_carryover", False)
            leave.status = LeaveRequest.Status.SUBMITTED
            leave.save()

            messages.success(request, "Wniosek urlopowy został wysłany.")
            return redirect("urlop_add")

        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

        context = self._build_context(request, form)
        return render(request, self.template_name, context)
