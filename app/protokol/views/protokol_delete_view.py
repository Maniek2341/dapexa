from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse

from app.protokol.models import Protocol
from app.protokol.permissions import can_manage_protocols
from django.core.exceptions import PermissionDenied


class ProtocolDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        if not can_manage_protocols(request.user):
            raise PermissionDenied

        protocol = get_object_or_404(
            Protocol,
            pk=pk,
            company=request.user.company
        )

        number = protocol.number
        protocol.delete()

        messages.success(request, f"Protokół {number} został usunięty.")
        return redirect(reverse("protokol_nowe"))  # albo lista protokołów
