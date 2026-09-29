from decimal import Decimal

from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages

from app.urlop.services import (
    get_allowance,
    get_leave_type_usage,
    used_vacation_days,
)
from app.urlop.models import LeaveAllowance, LeaveType, LeaveRequest
from app.urlop.access import LeavePermissionMixin
from app.urlop.allowance_generator import ensure_year_allowances, eligible_leave_users


class LeaveAllowanceListView(LeavePermissionMixin, View):
    leave_permission = "leave_allowance_list"
    login_url = reverse_lazy("login")
    template_name = "app/urlop/allowance_list.html"

    def get(self, request, *args, **kwargs):
        year = timezone.localdate().year

        employees = eligible_leave_users(request.user.company).order_by("first_name", "last_name")

        leave_types = LeaveType.objects.filter(
            company=request.user.company,
            counts_against_limit=True,
        ).order_by("name")

        data = []

        for employee in employees:
            base_limit = Decimal("0")
            try:
                allowance = get_allowance(request.user.company, employee, year)
                base_limit = allowance.vacation_limit

                vacation_limit = (
                    allowance.vacation_limit
                    + allowance.carryover_days
                    + allowance.adjustment_days
                )

                vacation_used = used_vacation_days(
                    request.user.company,
                    employee,
                    year,
                )

                vacation_remaining = vacation_limit - vacation_used
                carryover = allowance.carryover_days
                adjustment = allowance.adjustment_days

            except LeaveAllowance.DoesNotExist:
                vacation_limit = Decimal("0")
                vacation_used = Decimal("0")
                vacation_remaining = Decimal("0")
                carryover = Decimal("0")
                adjustment = Decimal("0")

            employee_leave_types = []

            for leave_type in leave_types:
                # klasyczny wypoczynkowy liczony z LeaveAllowance
                if leave_type.pool == "vacation" and not leave_type.is_special:
                    continue
                else:
                    usage = get_leave_type_usage(
                        request.user.company,
                        employee,
                        leave_type,
                        year,
                    )
                    employee_leave_types.append({
                        "name": leave_type.name,
                        "code": leave_type.code,
                        "limit": usage["limit"],
                        "used": usage["used"],
                        "remaining": usage["remaining"],
                    })

            data.append({
                "employee": employee,
                "limit": vacation_limit,
                "carryover": carryover,
                "adjustment": adjustment,
                "base_limit": base_limit,
                "used": vacation_used,
                "remaining": vacation_remaining,
                "leave_types": employee_leave_types,
            })

        return render(request, self.template_name, {
            "data": data,
            "year": year,
        })


class GenerateLeaveAllowancesView(LeavePermissionMixin, View):
    leave_permission = "generate_leave_allowances"

    def post(self, request):
        year = int(request.POST.get("year") or timezone.localdate().year)
        if year < 2000 or year > 2200:
            messages.error(request, "Nieprawidłowy rok limitu.")
            return redirect("leave_allowance_list")
        ensure_year_allowances(request.user.company, year)
        messages.success(request, "Limity urlopowe zostały wygenerowane.")
        return redirect("leave_allowance_list")
