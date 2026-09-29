from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views import View
from django.db import transaction
from datetime import timedelta

from app.core.models import PanelUser
from app.kalendarz.models import Event


class PersonalCalendarEventCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    @staticmethod
    def eligible_attendees(user):
        if not user.company_id:
            return PanelUser.objects.none()
        return PanelUser.objects.filter(
            company_id=user.company_id,
            is_active=True,
            is_active_employee=True,
        ).exclude(role__in=[PanelUser.Role.CLIENT, PanelUser.Role.PODWYKONAWCA]).order_by(
            "first_name", "last_name", "email",
        )

    def get(self, request):
        return redirect("user_calendar")

    def post(self, request):
        if (
            not request.user.company_id
            or request.user.role in {PanelUser.Role.CLIENT, PanelUser.Role.PODWYKONAWCA}
        ):
            raise PermissionDenied("Do dodania wydarzenia wymagane jest przypisanie do firmy.")
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        start = parse_datetime(request.POST.get("start", ""))
        end = parse_datetime(request.POST.get("end", ""))
        recurrence = request.POST.get("recurrence", Event.Recurrence.NONE)
        recurrence_until_raw = (request.POST.get("recurrence_until") or "").strip()
        recurrence_until = parse_date(recurrence_until_raw) if recurrence_until_raw else None
        errors = []
        if not title:
            errors.append("Podaj nazwę wydarzenia.")
        if start and timezone.is_naive(start):
            start = timezone.make_aware(start, timezone.get_current_timezone())
        if end and timezone.is_naive(end):
            end = timezone.make_aware(end, timezone.get_current_timezone())
        if not start or not end:
            errors.append("Podaj początek i koniec wydarzenia.")
        elif end <= start:
            errors.append("Koniec wydarzenia musi być późniejszy niż początek.")
        elif any((start.date() + timedelta(days=offset)).weekday() >= 5
                 for offset in range((end.date() - start.date()).days + 1)):
            errors.append("Nie można dodawać wydarzeń w weekend ani wydarzeń obejmujących weekend.")
        elif recurrence not in Event.Recurrence.values:
            errors.append("Wybierz poprawny harmonogram wydarzenia.")
        elif recurrence == Event.Recurrence.DAILY:
            if start.date() != end.date():
                errors.append("Wydarzenie powtarzane codziennie musi odbywać się tego samego dnia.")
            if not recurrence_until:
                errors.append("Podaj datę zakończenia powtarzania.")
            elif recurrence_until < start.date():
                errors.append("Powtarzanie nie może kończyć się przed rozpoczęciem wydarzenia.")
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("user_calendar")
        selected_ids = request.POST.getlist("attendees")
        attendees = list(self.eligible_attendees(request.user).filter(pk__in=selected_ids))
        attendee_by_id = {user.pk: user for user in attendees}
        attendee_by_id[request.user.pk] = request.user
        with transaction.atomic():
            event = Event.objects.create(
                company=request.user.company,
                created_by=request.user,
                title=title,
                description=description,
                start=start,
                end=end,
                recurrence=recurrence,
                recurrence_until=recurrence_until if recurrence == Event.Recurrence.DAILY else None,
            )
            event.attendees.set(attendee_by_id.values())
        messages.success(request, "Wydarzenie zostało dodane i udostępnione wybranym osobom.")
        return redirect("user_calendar")
