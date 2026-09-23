import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.utils import timezone
from django.db.models import Q, Max, Prefetch

from app.protokol.models import Protocol
from app.serwis.models import ServiceOrder
from app.klient.models import Client, ClientActivity
from app.zadanie.models import Task
from app.praca.models import WorkOrder
from app.pojazd.models import Vehicle
from app.wsparcie.models import SupportReply, SupportTicket


class DashboardView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/core/dashboard.html"

    def get(self, request):
        user = request.user
        company = getattr(user, "company", None)

        today = timezone.localdate()
        now = timezone.now()
        thirty_days_ago = now - datetime.timedelta(days=30)
        next_14_days = today + datetime.timedelta(days=14)

        if not company:
            return render(request, self.template_name, {
                "user": user,
            })

        clients_qs = Client.objects.filter(
            company=company,
            is_active=True,
        )

        protocols_qs = Protocol.objects.filter(
            company=company,
        ).select_related("client", "service", "work_order")

        services_qs = ServiceOrder.objects.filter(
            company=company,
        ).select_related("client", "location")

        work_orders_qs = WorkOrder.objects.filter(
            company=company,
        ).select_related("client", "location")

        tasks_qs = Task.objects.filter(
            company=company,
        )

        # ======================
        # KPI
        # ======================

        kpi_clients_count = clients_qs.count()

        kpi_protocols_30d = protocols_qs.filter(
            created_at__gte=thirty_days_ago,
        ).count()

        kpi_services_to_do = services_qs.filter(
            status__in=["new", "in_progress", "forgoted"],
        ).count()

        kpi_protocols_to_invoice = protocols_qs.filter(
            status="do_zafakturowania",
        ).count()

        kpi_open_tasks = tasks_qs.exclude(
            status=Task.Status.DONE,
        ).count()

        # ======================
        # Alerty
        # ======================

        overdue_tasks_count = tasks_qs.filter(
            due_date__lt=today,
        ).exclude(
            status=Task.Status.DONE,
        ).count()

        protocols_to_invoice_count = kpi_protocols_to_invoice

        vehicle_qs = Vehicle.objects.filter(
            company=company,
            is_active=True,
        )

        # Terminy pojazdów wykorzystywane w alertach i sekcji dashboardu.
        vehicle_deadline_filter = (
            Q(insurance_valid_until__gte=today, insurance_valid_until__lte=next_14_days)
            | Q(inspection_valid_until__gte=today, inspection_valid_until__lte=next_14_days)
        )
        vehicle_deadlines_count = vehicle_qs.filter(vehicle_deadline_filter).count()
        warranty_alerts_count = 0

        # ======================
        # Zadania
        # ======================

        my_tasks = tasks_qs.filter(
            assignment_type=Task.AssignmentType.USER,
            assigned_user=user,
        ).exclude(
            status=Task.Status.DONE,
        ).order_by("due_date", "-created_at")[:8]

        role_tasks = tasks_qs.filter(
            assignment_type=Task.AssignmentType.ROLE,
            assigned_role=user.role,
        ).exclude(
            status=Task.Status.DONE,
        ).order_by("due_date", "-created_at")[:8]

        all_company_tasks = tasks_qs.filter(
            assignment_type=Task.AssignmentType.ALL,
        ).exclude(
            status=Task.Status.DONE,
        ).order_by("due_date", "-created_at")[:8]

        # ======================
        # Przypisane serwisy i prace
        # ======================

        assigned_services = list(
            services_qs
            .filter(assigned_to=user)
            .exclude(status__in=[ServiceOrder.Status.DONE, ServiceOrder.Status.CANCELLED])
            .distinct()
            .order_by("planned_start", "-created_at")[:8]
        )
        for service in assigned_services:
            service.is_overdue = (
                service.planned_start is not None
                and service.planned_start.date() < today
            )

        assigned_works = list(
            work_orders_qs
            .filter(assigned_employees=user)
            .exclude(status__in=[WorkOrder.Status.DONE, WorkOrder.Status.CANCELLED])
            .distinct()
            .order_by("planned_start", "-created_at")[:8]
        )
        for work in assigned_works:
            work.is_overdue = (
                work.planned_start is not None
                and work.planned_start.date() < today
            )

        # ======================
        # Dzisiejsze wydarzenia
        # ======================

        today_services = services_qs.filter(
            planned_start__date=today,
        ).order_by("planned_start")[:8]

        today_works = work_orders_qs.filter(
            planned_start__date=today,
        ).order_by("planned_start")[:8]

        today_events = []

        for service in today_services:
            today_events.append({
                "title": service.title or service.number,
                "client": service.client,
                "location": getattr(service, "location", None),
                "start": service.planned_start,
                "url_name": "serwis_detail",
                "pk": service.pk,
                "kind": "serwis",
            })

        for work in today_works:
            today_events.append({
                "title": work.title or work.number,
                "client": work.client,
                "location": getattr(work, "location", None),
                "start": work.planned_start,
                "url_name": "work_detail",
                "pk": work.pk,
                "kind": "praca",
            })

        today_events.sort(key=lambda event: event["start"] or now)
        today_events = today_events[:8]

        # ======================
        # Najbliższe serwisy
        # ======================

        upcoming_services = services_qs.filter(
            status__in=["new", "in_progress"],
        ).filter(
            planned_start__date__gte=today,
        ).order_by("planned_start", "-created_at")[:8]

        # ======================
        # Protokoły
        # ======================

        recent_protocols = protocols_qs.order_by(
            "-end_time",
            "-created_at",
        )[:5]

        protocols_to_invoice = protocols_qs.filter(
            status="do_zafakturowania",
        ).order_by("-end_time", "-created_at")[:8]

        # ======================
        # Najbliższe terminy
        # ======================

        deadlines = []

        upcoming_vehicle_deadlines = vehicle_qs.filter(
            vehicle_deadline_filter,
        ).order_by("insurance_valid_until", "inspection_valid_until")

        for vehicle in upcoming_vehicle_deadlines:
            for field_name, label in (
                ("insurance_valid_until", "OC"),
                ("inspection_valid_until", "Przegląd"),
            ):
                deadline_date = getattr(vehicle, field_name)
                if not deadline_date or not (today <= deadline_date <= next_14_days):
                    continue
                deadlines.append({
                    "title": f"{label}: {vehicle.registration_number}",
                    "description": f"{vehicle.brand} {vehicle.model}".strip(),
                    "date": deadline_date,
                    "days_left": (deadline_date - today).days,
                })

        deadlines = sorted(
            deadlines,
            key=lambda x: x["date"] or today,
        )[:8]

        # ======================
        # Ostatnia aktywność
        # ======================

        recent_activities_qs = ClientActivity.objects.filter(company=company)
        if not user.has_perm("core.access_employee_list"):
            recent_activities_qs = recent_activities_qs.filter(created_by=user)

        recent_activities = recent_activities_qs.select_related(
            "client",
            "created_by",
        ).order_by(
            "-created_at",
        )[:10]

        # Odpowiedzi wsparcia są widoczne tylko dla osób zarządzających panelem.
        show_support_updates = (
            user.is_superuser
            or user.role in {user.Role.OWNER, user.Role.MANAGER, user.Role.BIURO}
        )
        support_updates = []
        if show_support_updates:
            support_updates = SupportTicket.objects.filter(
                company=company,
                replies__isnull=False,
            ).prefetch_related(
                Prefetch(
                    "replies",
                    queryset=SupportReply.objects.select_related("author").order_by("-created_at"),
                    to_attr="dashboard_replies",
                )
            ).annotate(last_reply_at=Max("replies__created_at")).distinct().order_by("-last_reply_at")[:5]

        context = {
            "user": user,

            # KPI
            "kpi_protocols_30d": kpi_protocols_30d,
            "kpi_services_to_do": kpi_services_to_do,
            "kpi_protocols_to_invoice": kpi_protocols_to_invoice,
            "kpi_open_tasks": kpi_open_tasks,
            "kpi_clients_count": kpi_clients_count,

            # Alerty
            "overdue_tasks_count": overdue_tasks_count,
            "protocols_to_invoice_count": protocols_to_invoice_count,
            "vehicle_deadlines_count": vehicle_deadlines_count,
            "warranty_alerts_count": warranty_alerts_count,

            # Zadania
            "my_tasks": my_tasks,
            "role_tasks": role_tasks,
            "all_company_tasks": all_company_tasks,
            "assigned_services": assigned_services,
            "assigned_works": assigned_works,
            "today": today,
            "show_management_dashboard_sections": user.has_perm("core.access_employee_list"),

            # Dashboard
            "today_events": today_events,
            "upcoming_services": upcoming_services,
            "recent_protocols": recent_protocols,
            "protocols_to_invoice": protocols_to_invoice,
            "deadlines": deadlines,
            "recent_activities": recent_activities,
            "support_updates": support_updates,
            "show_support_updates": show_support_updates,
        }

        return render(request, self.template_name, context)
