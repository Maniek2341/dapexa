from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from django.urls import reverse

from app.protokol.models import ProtocolActivity, ProtokolImage
from app.protokol.permissions import can_manage_protocols
from django.core.exceptions import PermissionDenied


class ProtocolMediaDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        if not can_manage_protocols(request.user):
            raise PermissionDenied

        media = get_object_or_404(
            ProtokolImage,
            pk=pk,
            protokol__company=request.user.company
        )

        protocol = media.protokol
        protocol_id = media.protokol.pk

        file_name = media.original_name or media.file.name

        # usuń plik fizyczny
        if media.file:
            media.file.delete(save=False)

        media.delete()

        ProtocolActivity.objects.create(
            protocol=protocol,
            company=request.user.company,
            type=ProtocolActivity.Type.SYSTEM,  # dopasuj jeśli masz inne typy
            title="Usunięto załącznik",
            description=f"Usunięto plik: {file_name}",
            created_by=request.user
        )

        messages.success(request, "Załącznik został usunięty.")
        return redirect(reverse("protokol_detail", args=[protocol_id]))
