from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View

from app.protokol.models import Protocol, ProtocolActivity
from app.protokol.permissions import can_manage_protocols
from django.core.exceptions import PermissionDenied


class ProtocolStatusUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request, pk):
        if not can_manage_protocols(request.user):
            raise PermissionDenied

        protocol = get_object_or_404(
            Protocol,
            pk=pk,
            company=request.user.company
        )

        new_status = (request.POST.get("status") or "").strip()
        allowed = {choice[0] for choice in Protocol.Status.choices}

        if new_status not in allowed:
            messages.error(request, "Nieprawidłowy status.")
            return HttpResponseRedirect(
                reverse("protokol_detail", args=[protocol.pk])
            )

        old_status = protocol.status

        if new_status == old_status:
            messages.info(request, "Status bez zmian.")
            return HttpResponseRedirect(
                reverse("protokol_detail", args=[protocol.pk])
            )

        old_label = protocol.get_status_display()

        with transaction.atomic():

            # 🔥 Jeśli status = DO ZAFAKTUROWANIA → zapisz dane faktury
            if new_status == "do_zafakturowania":

                protocol.ile_vat = request.POST.get("vat")
                protocol.sposob_wysylki = request.POST.get("sposob_wysylki")

                protocol.czy_powykonawcza = (
                    request.POST.get("czy_powykonawcza") == "true"
                )

                typ = request.POST.get("protokol_typ")

                if typ == "z_cena":
                    protocol.protokol_ceny = True
                    protocol.protokol_bez_ceny = False
                elif typ == "bez_ceny":
                    protocol.protokol_ceny = False
                    protocol.protokol_bez_ceny = True

                protocol.dodatkowe_info_pracownik = request.POST.get(
                    "dodatkowe_info_pracownik", ""
                )

            # 🔥 zmiana statusu
            protocol.status = new_status
            protocol.save()

            new_label = protocol.get_status_display()

            desc = f"{old_label} → {new_label}"

            # jeśli to był etap fakturowania – dopisz szczegóły
            if new_status == "do_zafakturowania":
                desc += "\n\nPrzygotowano dane do faktury."

            ProtocolActivity.objects.create(
                company=protocol.company,
                protocol=protocol,
                type=ProtocolActivity.Type.STATUS,
                title="Zmieniono status",
                description=desc,
                created_by=request.user,
            )

        messages.success(request, "Zmieniono status protokołu.")
        return HttpResponseRedirect(
            reverse("protokol_detail", args=[protocol.pk])
        )
