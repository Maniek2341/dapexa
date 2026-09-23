# app/serwis/views/service_media_delete_view.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import View

from app.serwis.models import ServiceOrderMedia, ServiceActivity
from app.serwis.permissions import can_manage_services
from app.serwis.signals import log_service_activity


class ServiceMediaDeleteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request, pk):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może usuwać załączników serwisu.")

        media = get_object_or_404(
            ServiceOrderMedia.objects.select_related("service", "service__company"),
            pk=pk,
            service__company=request.user.company,
        )
        service = media.service

        name = media.original_name or getattr(media.file, "name", "") or "plik"
        kind = getattr(media, "kind", "")
        label = "Zdjęcie" if str(kind) == "image" or getattr(ServiceOrderMedia, "Kind", None) and kind == ServiceOrderMedia.Kind.IMAGE else "Załącznik"

        # usuń plik z storage + rekord
        try:
            if media.file:
                media.file.delete(save=False)
        except Exception:
            pass

        media.delete()

        # activity
        try:
            log_service_activity(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.SYSTEM,
                title=f"Usunięto {label.lower()}",
                description=f"{label}: {name}",
                user=request.user,
            )
        except Exception:
            ServiceActivity.objects.create(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.SYSTEM,
                title=f"Usunięto {label.lower()}",
                description=f"{label}: {name}",
                created_by=request.user,
            )

        messages.success(request, f"Usunięto {label.lower()}.")
        return HttpResponseRedirect(reverse("serwis_detail", args=[service.pk]))
