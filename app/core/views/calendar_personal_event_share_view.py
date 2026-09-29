from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View

from app.kalendarz.models import Event
from .calendar_personal_event_view import PersonalCalendarEventCreateView


class PersonalCalendarEventShareView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request, pk):
        event = get_object_or_404(
            Event.objects.filter(company=request.user.company, attendees=request.user).filter(
                Q(created_by=request.user) | Q(created_by__isnull=True),
            ),
            pk=pk,
        )
        selected_ids = request.POST.getlist("attendees")
        attendees = list(
            PersonalCalendarEventCreateView.eligible_attendees(request.user).filter(pk__in=selected_ids)
        )
        attendee_by_id = {user.pk: user for user in attendees}
        attendee_by_id[request.user.pk] = request.user
        event.attendees.set(attendee_by_id.values())
        messages.success(request, "Lista osób, którym udostępniono wydarzenie, została zaktualizowana.")
        return redirect("user_calendar")
