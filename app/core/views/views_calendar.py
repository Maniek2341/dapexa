# app/core/views_calendar.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from app.serwis.models import ServiceOrder
from app.praca.models import WorkOrder
from app.protokol.models import Protocol
from app.urlop.models import LeaveRequest
from app.kalendarz.models import Event
from app.core.models import CompanySettings, PanelUser

@login_required
def user_calendar_events(request):
    user = request.user

    events = []

    # 🔹 Protokoły
    protocols = ServiceOrder.objects.filter(company=user.company)
    works = WorkOrder.objects.filter(company=user.company)

    if getattr(user, "role", None) == user.Role.EMPLOYEE:
        protocols = protocols.filter(assigned_to=user)
        works = works.filter(assigned_employees=user)

    for p in protocols:
        if p.planned_start:
            events.append({
                "title": f"Serwis {p.number}",
                "start": p.planned_start.isoformat(),
                "end": p.planned_end.isoformat() if p.planned_end else None,
                "color": "#1a73e8",
                "url": reverse("serwis_detail", kwargs={"pk": p.pk}),
            })

    for work in works:
        if work.planned_start:
            events.append({
                "title": f"Praca {work.number}",
                "start": work.planned_start.isoformat(),
                "end": work.planned_end.isoformat() if work.planned_end else None,
                "color": "#1468f5",
                "url": reverse("work_detail", kwargs={"pk": work.pk}),
            })

    # 🔹 Urlopy
    leaves = LeaveRequest.objects.filter(company=user.company).filter(
        Q(status=LeaveRequest.Status.APPROVED)
        | Q(user=user, status=LeaveRequest.Status.SUBMITTED)
    ).select_related("user", "leave_type")

    for l in leaves:
        own = l.user_id == user.pk
        title = (
            f"Urlop ({l.leave_type.name}) {l.user.first_name} {l.user.last_name}"
            if own else "Nieobecność"
        )
        events.append({
            "title": title,
            "start": l.date_from.isoformat(),
            # FullCalendar traktuje datę końcową jako wyłączną.
            "end": (l.date_to + timedelta(days=1)).isoformat(),
            "allDay": True,
            "color": "#34a853" if l.status == LeaveRequest.Status.APPROVED else "#f9ab00",
        })

    range_start = parse_datetime(request.GET.get("start", ""))
    range_end = parse_datetime(request.GET.get("end", ""))
    if range_start and timezone.is_naive(range_start):
        range_start = timezone.make_aware(range_start, timezone.get_current_timezone())
    if range_end and timezone.is_naive(range_end):
        range_end = timezone.make_aware(range_end, timezone.get_current_timezone())

    for event in Event.objects.filter(company=user.company, attendees=user):
        base = {"title": event.title, "color": "#8b5cf6"}
        if event.recurrence != Event.Recurrence.DAILY or not event.recurrence_until:
            events.append({**base, "start": event.start.isoformat(), "end": event.end.isoformat()})
            continue

        # FullCalendar sends a date range. Without it, return just the first
        # occurrence to avoid expanding an unbounded feed.
        if not range_start or not range_end:
            dates = [event.start.date()]
        else:
            first_day = max(event.start.date(), timezone.localtime(range_start).date())
            last_day = min(
                event.recurrence_until,
                timezone.localtime(range_end - timedelta(microseconds=1)).date(),
            )
            dates = (
                first_day + timedelta(days=offset)
                for offset in range(max(0, (last_day - first_day).days + 1))
            )

        local_start = timezone.localtime(event.start)
        duration = event.end - event.start
        for occurrence_day in dates:
            if occurrence_day.weekday() >= 5 or occurrence_day > event.recurrence_until:
                continue
            occurrence_start = timezone.make_aware(
                datetime.combine(occurrence_day, local_start.timetz().replace(tzinfo=None)),
                timezone.get_current_timezone(),
            )
            occurrence_end = occurrence_start + duration
            if range_start and occurrence_end <= range_start:
                continue
            if range_end and occurrence_start >= range_end:
                continue
            events.append({
                **base,
                "id": f"{event.pk}-{occurrence_day.isoformat()}",
                "start": occurrence_start.isoformat(),
                "end": occurrence_end.isoformat(),
            })

    return JsonResponse(events, safe=False)


from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

class UserCalendarView(LoginRequiredMixin, View):
    template_name = "app/kalendarz/user_calendar.html"

    def get(self, request):
        settings = CompanySettings.objects.filter(company=request.user.company).only(
            "default_work_start_time", "default_work_end_time"
        ).first()
        calendar_users = PanelUser.objects.filter(
            company=request.user.company,
            is_active=True,
            is_active_employee=True,
        ).exclude(
            role__in=[PanelUser.Role.CLIENT, PanelUser.Role.PODWYKONAWCA],
        ).exclude(pk=request.user.pk).order_by("first_name", "last_name", "email")
        return render(request, self.template_name, {
            "personal_events": Event.objects.filter(
                company=request.user.company, attendees=request.user,
            ).select_related("created_by").prefetch_related("attendees").order_by("start"),
            "calendar_users": calendar_users,
            "calendar_start_time": settings.default_work_start_time.strftime("%H:%M:%S") if settings else "07:00:00",
            "calendar_end_time": settings.default_work_end_time.strftime("%H:%M:%S") if settings else "15:00:00",
        })
