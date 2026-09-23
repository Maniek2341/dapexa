# app/core/views_calendar.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from datetime import timedelta
from app.serwis.models import ServiceOrder
from app.praca.models import WorkOrder
from app.protokol.models import Protocol
from app.urlop.models import LeaveRequest
from app.kalendarz.models import Event
from app.core.models import CompanySettings

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
    leaves = LeaveRequest.objects.filter(company=user.company).select_related("user", "leave_type")

    for l in leaves:
        events.append({
            "title": f"Urlop ({l.leave_type.name}) {l.user.first_name} {l.user.last_name}",
            "start": l.date_from.isoformat(),
            # FullCalendar traktuje datę końcową jako wyłączną.
            "end": (l.date_to + timedelta(days=1)).isoformat(),
            "allDay": True,
            "color": "#34a853" if l.status == "approved" else "#ea4335",
        })

    for event in Event.objects.filter(company=user.company, attendees=user):
        events.append({
            "title": event.title,
            "start": event.start.isoformat(),
            "end": event.end.isoformat(),
            "color": "#8b5cf6",
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
        return render(request, self.template_name, {
            "personal_events": Event.objects.filter(
                company=request.user.company, attendees=request.user,
            ).order_by("start"),
            "calendar_start_time": settings.default_work_start_time.strftime("%H:%M:%S") if settings else "07:00:00",
            "calendar_end_time": settings.default_work_end_time.strftime("%H:%M:%S") if settings else "15:00:00",
        })
