from datetime import date
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
from app.core.models import PanelUser
from app.urlop.models import LeaveAllowance, LeaveType, LeaveRequest


class LeaveAllowanceListView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/urlop/allowance_list.html"

    def get(self, request, *args, **kwargs):
        year = timezone.now().year

        employees = PanelUser.objects.filter(
            company=request.user.company,
            is_active=True,
            is_active_employee=True,
        ).order_by("first_name", "last_name")

        leave_types = LeaveType.objects.filter(
            company=request.user.company,
            counts_against_limit=True,
        ).order_by("name")

        data = []

        for employee in employees:
            try:
                allowance = get_allowance(request.user.company, employee, year)

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
                if vacation_remaining < 0:
                    vacation_remaining = Decimal("0")

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
                "used": vacation_used,
                "remaining": vacation_remaining,
                "leave_types": employee_leave_types,
            })

        return render(request, self.template_name, {
            "data": data,
            "year": year,
        })


class GenerateLeaveAllowancesView(LoginRequiredMixin, View):
    def get(self, request):
        if request.user.role != "owner":
            return redirect("dashboard")

        company = request.user.company
        year = timezone.now().year
        previous_year = year - 1

        employees = PanelUser.objects.filter(
            company=company,
            role__in=["owner", "manager", "employee"],
            is_active_employee=True,
        )

        for emp in employees:
            # 1. podstawowy limit 20/26 × etat
            limit = emp.get_vacation_entitlement()

            # 2. zaległy z poprzedniego roku - tylko wypoczynkowy
            carryover = Decimal("0")

            try:
                prev_allowance = LeaveAllowance.objects.get(
                    company=company,
                    user=emp,
                    year=previous_year,
                )

                used_last_year = used_vacation_days(
                    company,
                    emp,
                    previous_year,
                )

                total_last_year = (
                    prev_allowance.vacation_limit
                    + prev_allowance.carryover_days
                    + prev_allowance.adjustment_days
                )

                remaining = total_last_year - used_last_year

                if remaining > 0:
                    carryover = remaining

            except LeaveAllowance.DoesNotExist:
                pass

            # 3. zapis nowego roku
            LeaveAllowance.objects.update_or_create(
                company=company,
                user=emp,
                year=year,
                defaults={
                    "vacation_limit": limit,
                    "carryover_days": carryover,
                    "adjustment_days": Decimal("0"),
                    "on_demand_limit": Decimal("4"),
                    "carryover_deadline": date(year, 9, 30),
                }
            )

        messages.success(request, "Limity urlopowe zostały wygenerowane.")
        return redirect("leave_allowance_list")