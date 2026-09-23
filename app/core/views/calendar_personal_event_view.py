from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View

from app.kalendarz.models import Event


class PersonalCalendarEventCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request):
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        start = parse_datetime(request.POST.get("start", ""))
        end = parse_datetime(request.POST.get("end", ""))
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
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("user_calendar")
        event = Event.objects.create(company=request.user.company, title=title, description=description, start=start, end=end)
        event.attendees.add(request.user)
        messages.success(request, "Dodano wydarzenie do Twojego kalendarza.")
        return redirect("user_calendar")
