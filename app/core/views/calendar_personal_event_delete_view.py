from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.db.models import Q

from app.kalendarz.models import Event


class PersonalCalendarEventDeleteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request, pk):
        event = get_object_or_404(
            Event.objects.filter(company=request.user.company, attendees=request.user).filter(
                Q(created_by=request.user) | Q(created_by__isnull=True),
            ),
            pk=pk,
        )
        event.delete()
        messages.success(request, "Wydarzenie zostało usunięte.")
        return redirect("user_calendar")
