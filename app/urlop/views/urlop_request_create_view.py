from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View

from app.urlop.access import LeavePermissionMixin
from app.urlop.forms import LeaveRequestForm
from app.urlop.models import LeaveRequest
from app.urlop.services import get_leave_limits_for_user, get_remaining_days, submit_leave_request
from app.urlop.allowance_generator import ensure_employee_year_allowance
from app.core.notifications import notify_company_email
import holidays


class LeaveRequestCreateView(LeavePermissionMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/urlop/urlop_add.html"
    leave_permission = "urlop_add"

    def _build_context(self, request, form):
        year = timezone.localdate().year
        ensure_employee_year_allowance(request.user.company, request.user, year)
        limits_by_year = {
            item_year: {
                    str(item["leave_type"].pk): {
                        "name": item["leave_type"].name, "limit": str(item["limit"]),
                        "used": str(item["used"]), "remaining": str(item["remaining"]),
                        "carryover_remaining": str(item["carryover_remaining"]),
                    } for item in get_leave_limits_for_user(request.user.company, request.user, item_year)
            }
            for item_year in range(year - 1, year + 4)
        }
        limits = get_leave_limits_for_user(request.user.company, request.user, year)
        public_holidays = holidays.country_holidays("PL", years=range(year - 1, year + 4))
        return {
            "form": form,
            "remaining_days": get_remaining_days(request.user.company, request.user, year),
            "leave_limits": limits,
            "leave_limits_map": limits_by_year,
            "public_holidays": [day.isoformat() for day in public_holidays],
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self._build_context(request, LeaveRequestForm(user=request.user)))

    def post(self, request, *args, **kwargs):
        form = LeaveRequestForm(request.POST, user=request.user)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.company = request.user.company
            leave.user = request.user
            leave.leave_year = form.cleaned_data["leave_year"]
            leave.is_carryover = form.cleaned_data.get("is_carryover", False)
            try:
                submit_leave_request(leave)
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                notify_company_email(
                    company=leave.company,
                    module="urlop",
                    subject=f"Nowy wniosek urlopowy: {leave.user.get_full_name() or leave.user.email}",
                    message=(
                        f"{leave.user.get_full_name() or leave.user.email} złożył wniosek urlopowy.\n"
                        f"Rodzaj: {leave.leave_type.name}\n"
                        f"Termin: {leave.date_from:%d.%m.%Y} – {leave.date_to:%d.%m.%Y}\n"
                        f"Liczba dni roboczych: {leave.days_count}"
                    ),
                )
                messages.success(request, "Wniosek urlopowy został wysłany.")
                return redirect("urlop_add")
        return render(request, self.template_name, self._build_context(request, form))


class MyLeaveCancelView(LeavePermissionMixin, View):
    leave_permission = "urlop_add"

    def post(self, request, pk):
        leave = get_object_or_404(
            LeaveRequest, pk=pk, company=request.user.company, user=request.user,
        )
        if leave.status != LeaveRequest.Status.SUBMITTED:
            messages.error(request, "Można wycofać tylko oczekujący wniosek.")
            return redirect("profile")
        from django.db import transaction
        from app.core.models import PanelUser
        with transaction.atomic():
            PanelUser.objects.select_for_update().get(pk=request.user.pk)
            leave = LeaveRequest.objects.select_for_update().get(
                pk=pk, company=request.user.company, user=request.user,
            )
            if leave.status != LeaveRequest.Status.SUBMITTED:
                messages.error(request, "Wniosek został już rozpatrzony.")
                return redirect("profile")
            leave.status = LeaveRequest.Status.CANCELLED
            leave.save()
        messages.success(request, "Wniosek został wycofany.")
        return redirect("profile")
