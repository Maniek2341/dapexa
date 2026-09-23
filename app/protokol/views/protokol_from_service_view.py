from django.db import transaction
from app.serwis.models import ServiceActivity, ServiceOrder
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal
from django.contrib import messages

from app.protokol.forms import ProtocolCreateForm, ProtokolUrzadzeniaFormSet
from app.protokol.models import Protocol, ProtokolUrzadzenia, ProtokolImage, ProtocolActivity
from app.urzadzenie.models import Product
from django.core.exceptions import PermissionDenied

class ProtocolFromServiceView(LoginRequiredMixin, View):

    template_name = "app/protokol/add.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm("protokol.access_protocol_from_service"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        service = get_object_or_404(
            ServiceOrder,
            pk=pk,
            company=request.user.company
        )

        form = ProtocolCreateForm(
            user=request.user
        )

        # 🔥 usuń pola z formularza
        for field in ["client", "location", "title"]:
            form.fields.pop(field, None)

        formset = ProtokolUrzadzeniaFormSet(
            form_kwargs={"user": request.user}
        )

        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "service": service,
            "from_service": True
        })
    
    def post(self, request, pk):

        service = get_object_or_404(
            ServiceOrder,
            pk=pk,
            company=request.user.company
        )

        form = ProtocolCreateForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        for field in ["client", "location", "title"]:
            form.fields.pop(field, None)

        formset = ProtokolUrzadzeniaFormSet(
            request.POST,
            form_kwargs={"user": request.user}
        )

        if form.is_valid() and formset.is_valid():

            hourly_logs = service.work_logs.all() if service.settlement_method == ServiceOrder.SettlementMethod.HOURLY else []
            if service.settlement_method == ServiceOrder.SettlementMethod.HOURLY and not hourly_logs.exists():
                messages.error(request, "Dodaj co najmniej jeden dzienny wpis pracy przed utworzeniem protokołu.")
                return redirect("serwis_detail", service.pk)

            with transaction.atomic():

                # 🔹 TWORZENIE PROTOKOŁU
                protocol = form.save(commit=False)

                protocol.company = request.user.company
                protocol.pracownik = request.user
                protocol.client = service.client
                protocol.title = f"Protokół do serwisu {service.number}"
                protocol.service = service
                protocol.protocol_description = service.description
                protocol.address = service.address  # FK

                protocol.address_street = service.address_street
                protocol.address_city = service.address_city
                protocol.address_postal_code = service.address_postal_code
                protocol.address_country = service.address_country
                protocol.address_latitude = service.address_latitude
                protocol.address_longitude = service.address_longitude

                if service.settlement_method == ServiceOrder.SettlementMethod.HOURLY:
                    logs = list(hourly_logs)
                    protocol.robocizna = sum((Decimal(str(log.hours or 0)) for log in logs), Decimal("0"))
                    protocol.pracownicy_szt = sum(log.workers_count or 0 for log in logs)
                    protocol.dojazdy_szt = sum(log.travel_count or 0 for log in logs)
                    protocol.wykonane_prace = "\n".join(
                        f"{log.work_date:%d.%m.%Y}: {log.performed_work}" for log in logs if log.performed_work
                    )[:250]
                    protocol.dodatkowe_materialy = "\n".join(
                        f"{log.work_date:%d.%m.%Y}: {log.materials}" for log in logs if log.materials
                    )[:250]

                protocol.save()

                # 🔹 ZAPIS MATERIAŁÓW
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

                # 🔥 PRZELICZ CAŁOŚĆ (model robi wszystko)
                protocol.recalculate(request.user)
                protocol.save()

                # 🔹 ZMIANA STATUSU SERWISU
                service.status = ServiceOrder.Status.DONE
                service.save(update_fields=["status"])

                # 🔹 HISTORIA SERWISU
                ServiceActivity.objects.create(
                    service=service,
                    company=request.user.company,
                    type="status",
                    title="Utworzono protokół",
                    description=f"Utworzono protokół {protocol.number} i oznaczono serwis jako zakończony.",
                    created_by=request.user
                )

                # 🔹 HISTORIA PROTOKOŁU
                ProtocolActivity.objects.create(
                    protocol=protocol,
                    company=request.user.company,
                    type="system",
                    title="Protokół utworzony z serwisu",
                    description=f"Protokół utworzony na podstawie serwisu {service.number}.",
                    created_by=request.user
                )

            messages.success(
                request,
                "Protokół został utworzony, serwis zakończony i dodano wpisy do historii."
            )

            return redirect("protokol_detail", protocol.pk)

        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "service": service,
            "from_service": True
        })
