from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View

from app.serwis.models import ServiceOrder, ServiceActivity, ServiceNote
from app.serwis.permissions import can_manage_services
# jeśli masz helper:
# from app.serwis.signals import log_service_activity

class SerwisStatusUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może zmieniać statusu serwisu.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        service = get_object_or_404(ServiceOrder, pk=pk, company=request.user.company)

        new_status = (request.POST.get("status") or "").strip()
        allowed = {"new", "forgoted", "in_progress"}

        if new_status not in allowed:
            messages.error(request, "Nieprawidłowy status.")
            return HttpResponseRedirect(reverse("serwis_detail", args=[service.pk]))

        progress_note = (request.POST.get("progress_note") or "").strip()

        if new_status == "in_progress" and not progress_note:
            messages.error(request, "Dla statusu „W trakcie” wpisz notatkę.")
            return HttpResponseRedirect(reverse("serwis_detail", args=[service.pk]))

        old_status = service.status

        if new_status == old_status:
            messages.info(request, "Status bez zmian.")
            return HttpResponseRedirect(reverse("serwis_detail", args=[service.pk]))

        # 👉 label starego statusu (czytelny)
        old_label = service.get_status_display()

        with transaction.atomic():
            service.status = new_status
            service.save(update_fields=["status"])

            # 👉 label nowego statusu (po zapisie)
            new_label = service.get_status_display()

            note_obj = None
            if new_status == "in_progress":
                note_obj = ServiceNote.objects.create(
                    company=service.company,
                    service=service,
                    author=request.user,
                    content=progress_note,
                )

            # ✅ ładny opis do logów
            desc = f"{old_label} → {new_label}"

            if note_obj:
                desc += f"\n\nNotatka:\n{progress_note}"

            ServiceActivity.objects.create(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.STATUS,
                title="Zmieniono status",
                description=desc,
                created_by=request.user,
            )

        messages.success(request, "Zmieniono status serwisu.")
        return HttpResponseRedirect(reverse("serwis_detail", args=[service.pk]))
