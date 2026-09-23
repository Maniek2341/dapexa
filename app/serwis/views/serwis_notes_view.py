from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View

from app.serwis.activity import log_service_activity
from app.serwis.models import ServiceActivity, ServiceOrder, ServiceNote
from app.serwis.forms import ServiceNoteForm
from app.serwis.permissions import can_manage_services


class ServiceNoteAddView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może dodawać notatek serwisowych.")

        service = get_object_or_404(ServiceOrder, pk=pk, company=request.user.company)
        form = ServiceNoteForm(request.POST)

        if form.is_valid():
            note = form.save(commit=False)
            note.company = request.user.company
            note.service = service
            note.author = request.user
            note.save()

            log_service_activity(
                company=request.user.company,
                service=service,
                type=ServiceActivity.Type.NOTE,
                title="Dodano notatkę",
                description=note.content,
                user=request.user,
            )
            messages.success(request, "Notatka dodana.")
        else:
            messages.error(request, "Nie udało się dodać notatki.")

        return HttpResponseRedirect(reverse("serwis_detail", kwargs={"pk": service.pk}) + "#notesBox")


class ServiceNotePinView(LoginRequiredMixin, View):
    def post(self, request, note_pk):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może przypinać notatek serwisowych.")

        note = get_object_or_404(ServiceNote, pk=note_pk, company=request.user.company)
        note.is_pinned = not note.is_pinned
        note.save(update_fields=["is_pinned"])
        log_service_activity(
            company=request.user.company,
            service=note.service,
            type=ServiceActivity.Type.NOTE,
            title=("Przypięto notatkę" if note.is_pinned else "Odpięto notatkę"),
            description=(note.content[:300] if note.content else ""),
            user=request.user,
        )
        return HttpResponseRedirect(reverse("serwis_detail", kwargs={"pk": note.service_id}) + "#notesBox")


class ServiceNoteDeleteView(LoginRequiredMixin, View):
    def post(self, request, note_pk):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może usuwać notatek serwisowych.")

        note = get_object_or_404(ServiceNote, pk=note_pk, company=request.user.company)
        service_id = note.service_id
        log_service_activity(
            company=request.user.company,
            service=note.service,
            type=ServiceActivity.Type.OTHER,
            title="Usunięto notatkę",
            description=(note.content[:300] if note.content else ""),
            user=request.user,
        )
        note.delete()
        messages.success(request, "Notatka usunięta.")
        return HttpResponseRedirect(reverse("serwis_detail", kwargs={"pk": service_id}) + "#notesBox")
