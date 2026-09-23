from collections import defaultdict
from decimal import Decimal
import pdfkit

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from app.core.models import PanelUser
from app.core.pdf_utils import get_company_logo_url
from app.rcp.models import TimeEntry


class TimeEntryPdfView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def get(self, request, *args, **kwargs):
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

        entries = TimeEntry.objects.filter(
            company=user.company,
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
            "1": "styczeń",
            "2": "luty",
            "3": "marzec",
            "4": "kwiecień",
            "5": "maj",
            "6": "czerwiec",
            "7": "lipiec",
            "8": "sierpień",
            "9": "wrzesień",
            "10": "październik",
            "11": "listopad",
            "12": "grudzień",
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

        work_days_count = len(work_days)

        avg_daily_hours = Decimal("0")
        if work_days_count > 0:
            avg_daily_hours = total_hours / Decimal(str(work_days_count))

        daily_overtime = {}

        for date, total in daily_totals.items():
            if total > Decimal("8"):
                daily_overtime[date] = total - Decimal("8")
            else:
                daily_overtime[date] = Decimal("0")

        context = {
            "entries": entries_list,
            "viewed_user": viewed_user,
            "company": user.company,
            "generated_at": timezone.localtime(),
            "active_month_label": active_month_label,
            "active_year": year,
            "active_month_num": month_num,
            "total_hours": total_hours,
            "work_days_count": work_days_count,
            "avg_daily_hours": avg_daily_hours,
            "overtime_hours": overtime_hours,
            "daily_overtime": daily_overtime,
            "company_logo_url": get_company_logo_url(request, user.company),
        }

        html = render_to_string("app/pdf/time_entry_report.html", context, request=request)

        config = getattr(settings, "WKHTMLTOPDF_CONFIG", None)
        options = {
            "encoding": "UTF-8",
            "page-size": "A4",
            "margin-top": "10mm",
            "margin-right": "10mm",
            "margin-bottom": "10mm",
            "margin-left": "10mm",
            "enable-local-file-access": "",
            "quiet": "",
        }

        try:
            pdf = pdfkit.from_string(
                html,
                False,
                configuration=config,
                options=options,
            )
        except Exception:
            messages.error(request, "Nie udało się wygenerować PDF.")
            return redirect("time_entry_list")

        filename = f"Lista_godzin_{viewed_user.first_name}_{viewed_user.last_name}_{year}_{month_num}.pdf"

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
