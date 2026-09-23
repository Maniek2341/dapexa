from collections import defaultdict
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.utils import timezone

from app.rcp.models import TimeEntry
from app.core.models import PanelUser


class CompanyQuerysetMixin:
    def get_company_queryset(self):
        return TimeEntry.objects.filter(company=self.request.user.company).select_related(
            "user",
            "approved_by",
            "rejected_by",
        )


class TimeEntryListView(LoginRequiredMixin, CompanyQuerysetMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/rcp/timeentry_list.html"

    def get(self, request):
        user = request.user

        can_choose_employee = user.role in [
            PanelUser.Role.OWNER,
            PanelUser.Role.MANAGER,
            PanelUser.Role.BIURO,
        ]

        selected_user_id = (request.GET.get("user") or "").strip()

        employees = PanelUser.objects.filter(
            company=user.company,
            is_active=True,
            is_active_employee=True,
        ).exclude(
            role=PanelUser.Role.CLIENT
        ).order_by("first_name", "last_name", "email")

        viewed_user = user

        if can_choose_employee and selected_user_id:
            try:
                viewed_user = employees.get(pk=selected_user_id)
            except (PanelUser.DoesNotExist, ValueError):
                viewed_user = user
                selected_user_id = ""

        entries = self.get_company_queryset().filter(
            user=viewed_user
        ).order_by("-date", "-created_at")

        year = (request.GET.get("year") or "").strip()
        month_num = (request.GET.get("month_num") or "").strip()

        today = timezone.localdate()

        if not year:
            year = str(today.year)

        if not month_num:
            month_num = str(today.month)

        if year:
            try:
                entries = entries.filter(date__year=int(year))
            except ValueError:
                pass

        if month_num:
            try:
                entries = entries.filter(date__month=int(month_num))
            except ValueError:
                pass

        month_labels = {
            "1": "sty",
            "2": "lut",
            "3": "mar",
            "4": "kwi",
            "5": "maj",
            "6": "cze",
            "7": "lip",
            "8": "sie",
            "9": "wrz",
            "10": "paź",
            "11": "lis",
            "12": "gru",
        }

        active_month_label = ""
        if month_num in month_labels and year:
            active_month_label = f"{month_labels[month_num]} {year}"

        entries_list = list(entries)

        total_hours = Decimal("0")
        work_days = set()
        daily_totals = defaultdict(lambda: Decimal("0"))

        for entry in entries_list:
            duration = entry.duration_hours or Decimal("0")
            total_hours += duration
            work_days.add(entry.date)
            daily_totals[entry.date] += duration

        overtime_hours = Decimal("0")
        daily_norm = Decimal("8")

        for day_total in daily_totals.values():
            if day_total > daily_norm:
                overtime_hours += (day_total - daily_norm)

        entries_count = len(entries_list)
        work_days_count = len(work_days)

        avg_daily_hours = Decimal("0")
        if work_days_count > 0:
            avg_daily_hours = total_hours / Decimal(str(work_days_count))

        can_direct_manage_own_entries = user.role in [
            PanelUser.Role.OWNER,
            PanelUser.Role.MANAGER,
            PanelUser.Role.BIURO,
        ]

        is_viewing_own_entries = viewed_user.id == user.id
        can_edit_delete_directly = can_direct_manage_own_entries and is_viewing_own_entries
        should_request_edit = user.role == PanelUser.Role.EMPLOYEE and is_viewing_own_entries

        context = {
            "entries": entries_list,
            "active_year": year,
            "active_month_num": month_num,
            "active_month_label": active_month_label,
            "total_hours": total_hours,
            "work_days_count": work_days_count,
            "avg_daily_hours": avg_daily_hours,
            "overtime_hours": overtime_hours,
            "entries_count": entries_count,

            "can_choose_employee": can_choose_employee,
            "employees": employees,
            "selected_user_id": str(viewed_user.id) if viewed_user else "",
            "viewed_user": viewed_user,

            "can_edit_delete_directly": can_edit_delete_directly,
            "should_request_edit": should_request_edit,
        }

        return render(request, self.template_name, context)