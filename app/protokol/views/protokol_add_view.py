from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from app.core.routing import RoutingService
from decimal import Decimal

from app.protokol.forms import ProtocolCreateForm, ProtokolUrzadzeniaFormSet
from app.protokol.models import Protocol, ProtokolUrzadzenia, ProtokolImage, ProtocolActivity
from app.urzadzenie.models import Product


class ProtokolAddView(LoginRequiredMixin, View):

    template_name = "app/protokol/add.html"

    def get(self, request):
        form = ProtocolCreateForm(user=request.user)

        formset = ProtokolUrzadzeniaFormSet(
            prefix="urzadzenia",
            form_kwargs={"user": request.user}
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset
            }
        )

    def post(self, request):

        form = ProtocolCreateForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        formset = ProtokolUrzadzeniaFormSet(
            request.POST,
            prefix="urzadzenia",
            form_kwargs={"user": request.user}
        )

        if not form.is_valid() or not formset.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "formset": formset
                }
            )

        protocol = form.save(commit=False)

        protocol.company = request.user.company
        protocol.pracownik = request.user

        # 🔥 ZAPIS NAJPIERW
        protocol.save()

        # 🔥 ZAPIS MATERIAŁÓW
        formset.instance = protocol

        items = formset.save(commit=False)

        for item in items:

            price = item.urzadzenia.net_price or Decimal("0.00")
            qty = item.sztuki or 0

            item.cenarazem = Decimal(qty) * Decimal(price)

            item.protokol = protocol

            item.save()

        formset.save_m2m()

        # 🔥 JEDNA LINIA – CAŁE LICZENIE
        protocol.recalculate(request.user)
        protocol.save()

        # ---------------------------
        # ZAŁĄCZNIKI
        # ---------------------------

        files = request.FILES.getlist("attachments[]")

        for file in files:
            ProtokolImage.objects.create(
                protokol=protocol,
                image=file
            )

        # ---------------------------
        # AKTYWNOŚĆ
        # ---------------------------

        ProtocolActivity.objects.create(
            company=request.user.company,
            protocol=protocol,
            type=ProtocolActivity.Type.SYSTEM,
            title="Utworzono protokół",
            description=f"Numer: {protocol.number}",
            created_by=request.user
        )

        messages.success(request, "Protokół został utworzony.")
        return redirect(reverse("protokol_add"))