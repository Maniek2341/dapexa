# app/protokol/views/protocol_from_work_view.py

from decimal import Decimal

from django.db import transaction, IntegrityError
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from app.praca.models import WorkOrder, WorkActivity
from app.protokol.forms import ProtocolCreateForm, ProtokolUrzadzeniaFormSet
from app.protokol.models import ProtocolActivity, Protocol


class ProtocolFromWorkView(LoginRequiredMixin, View):
    template_name = "app/protokol/add.html"

    def get(self, request, pk):
        work = get_object_or_404(
            WorkOrder,
            pk=pk,
            company=request.user.company,
        )

        form = ProtocolCreateForm(user=request.user)

        for field in ["client", "location", "title"]:
            form.fields.pop(field, None)

        formset = ProtokolUrzadzeniaFormSet(
            form_kwargs={"user": request.user}
        )

        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "work": work,
            "from_work": True,
        })

    def post(self, request, pk):
        work = get_object_or_404(
            WorkOrder,
            pk=pk,
            company=request.user.company,
        )

        form = ProtocolCreateForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        for field in ["client", "location", "title"]:
            form.fields.pop(field, None)

        formset = ProtokolUrzadzeniaFormSet(
            request.POST,
            form_kwargs={"user": request.user},
        )

        if form.is_valid() and formset.is_valid():
            if Protocol.objects.filter(work_order=work).exists():
                messages.error(
                    request,
                    "Do tej pracy został już utworzony protokół."
                )
                return redirect("work_detail", pk=work.pk)
            try:
                with transaction.atomic():

                    protocol = form.save(commit=False)

                    protocol.company = request.user.company
                    protocol.pracownik = request.user
                    protocol.client = work.client
                    protocol.title = f"Protokół do pracy {work.number}"

                    # jeśli dodasz pole work_order w Protocol
                    protocol.work_order = work

                    protocol.protocol_description = work.description

                    # lokalizacja / adres
                    if work.location:
                        protocol.location = work.location

                    # jeśli Protocol ma pole address, a lokalizacja ma address
                    if work.location and hasattr(work.location, "address"):
                        protocol.address = work.location.address

                    protocol.save()

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

                    protocol.recalculate(request.user)
                    protocol.save()

                    work.status = WorkOrder.Status.DONE
                    work.save(update_fields=["status"])

                    WorkActivity.objects.create(
                        work=work,
                        company=request.user.company,
                        type=WorkActivity.Type.STATUS,
                        title="Utworzono protokół",
                        description=f"Utworzono protokół {protocol.number} i oznaczono pracę jako zakończoną.",
                        created_by=request.user,
                    )

                    ProtocolActivity.objects.create(
                        protocol=protocol,
                        company=request.user.company,
                        type="system",
                        title="Protokół utworzony z pracy",
                        description=f"Protokół utworzony na podstawie pracy {work.number}.",
                        created_by=request.user,
                    )

                messages.success(
                    request,
                    "Protokół został utworzony, praca zakończona i dodano wpisy do historii."
                )

                return redirect("protokol_detail", protocol.pk)
                
            except IntegrityError:
                messages.error(
                    request,
                    "Do tej pracy został już utworzony protokół."
                )
                return redirect("work_detail", pk=work.pk)

        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "work": work,
            "from_work": True,
        })
