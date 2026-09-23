from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal

from app.protokol.models import Protocol, ProtocolActivity
from app.protokol.forms import ProtocolCreateForm, ProtokolUrzadzeniaFormSet
from app.protokol.permissions import can_manage_protocols
from django.core.exceptions import PermissionDenied


class ProtocolEditView(LoginRequiredMixin, View):

    template_name = "app/protokol/edit.html"

    # ---------------------------------------------------
    # POBIERANIE OBIEKTU
    # ---------------------------------------------------

    def get_object(self, request, pk):
        return get_object_or_404(
            Protocol,
            pk=pk,
            company=request.user.company
        )

    # ---------------------------------------------------
    # GET
    # ---------------------------------------------------

    def get(self, request, pk):

        if not can_manage_protocols(request.user):
            raise PermissionDenied

        protocol = self.get_object(request, pk)

        form = ProtocolCreateForm(
            instance=protocol,
            user=request.user
        )

        formset = ProtokolUrzadzeniaFormSet(
            instance=protocol,
            form_kwargs={"user": request.user}
        )

        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "protocol": protocol,
            "is_edit": True
        })

    # ---------------------------------------------------
    # POST
    # ---------------------------------------------------

    def post(self, request, pk):

        if not can_manage_protocols(request.user):
            raise PermissionDenied

        protocol = self.get_object(request, pk)

        form = ProtocolCreateForm(
            request.POST,
            request.FILES,
            instance=protocol,
            user=request.user
        )

        formset = ProtokolUrzadzeniaFormSet(
            request.POST,
            instance=protocol,
            form_kwargs={"user": request.user}
        )

        if form.is_valid() and formset.is_valid():

            # 🔹 zapisz podstawowe dane
            protocol = form.save(commit=False)
            protocol.save()

            # 🔹 zapisz materiały (usuń/dodaj/zmień)
            formset.instance = protocol

            items = formset.save(commit=False)

            for item in items:
                item.protokol = protocol

                price = item.urzadzenia.net_price or Decimal("0.00")
                qty = item.sztuki or 0

                item.cenarazem = Decimal(qty) * Decimal(price)
                item.save()

            for deleted in formset.deleted_objects:
                deleted.delete()

            # 🔥 PRZELICZ WSZYSTKO (logika w modelu)
            protocol.recalculate(request.user)
            protocol.save()

            # =========================================
            # 📝 HISTORIA
            # =========================================

            ProtocolActivity.objects.create(
                protocol=protocol,
                company=request.user.company,
                type=ProtocolActivity.Type.SYSTEM,
                title="Zaktualizowano protokół",
                description=f"Protokół {protocol.number} został edytowany.",
                created_by=request.user
            )

            messages.success(request, "Protokół został zaktualizowany.")
            return redirect(
                reverse("protokol_detail", args=[protocol.pk])
            )

        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "protocol": protocol,
            "is_edit": True
        })
