from datetime import datetime, time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View

from app.oferta_praca.models import Offer, OfferActivity
from app.praca.models import WorkOrder, WorkActivity


User = get_user_model()


class OfferForwardToExecutionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        offer = get_object_or_404(
            Offer.objects.prefetch_related("variants", "assigned_employees"),
            pk=pk,
            company=request.user.company,
        )

        if WorkOrder.objects.filter(offer=offer, company=offer.company).exists():
            messages.error(request, "Ta oferta została już przekazana do realizacji.")
            return redirect("offer_detail", pk=offer.pk)

        selected_variants = offer.variants.filter(is_selected=True)

        if not selected_variants.exists():
            messages.error(
                request,
                "Aby przekazać ofertę do realizacji, wybierz przynajmniej jeden wariant."
            )
            return redirect("offer_detail", pk=offer.pk)

        def parse_execution_date(value):
            value = (value or "").strip()
            if not value:
                return None
            parsed = parse_datetime(value)
            if parsed is None:
                from django.utils.dateparse import parse_date

                parsed_date = parse_date(value)
                parsed = datetime.combine(parsed_date, time.min) if parsed_date else None
            return parsed

        planned_start = parse_execution_date(request.POST.get("planned_start"))
        planned_end = parse_execution_date(request.POST.get("planned_end"))

        # Pola datetime-local przesyłają czas bez strefy — zapisz go jako
        # świadomy czas Django, tak jak pozostałe terminy w module pracy.
        if planned_start and timezone.is_naive(planned_start):
            planned_start = timezone.make_aware(
                planned_start, timezone.get_current_timezone()
            )
        if planned_end and timezone.is_naive(planned_end):
            planned_end = timezone.make_aware(
                planned_end, timezone.get_current_timezone()
            )
        execution_note = (request.POST.get("execution_note") or "").strip()

        workers_ids = request.POST.getlist("workers")

        assigned_employees = list(
            User.objects.filter(
                pk__in=workers_ids,
                company=request.user.company,
                is_active=True,
            )[:3]
        )

        if not assigned_employees:
            assigned_employees = list(offer.assigned_employees.all())

        total_netto = sum((v.total_netto or Decimal("0") for v in selected_variants), Decimal("0"))
        total_brutto = sum((v.total_brutto or Decimal("0") for v in selected_variants), Decimal("0"))

        try:
            with transaction.atomic():
                work_order = WorkOrder.objects.create(
                    company=offer.company,
                    offer=offer,
                    client=offer.client,
                    location=offer.location,
                    number=WorkOrder.generate_number(offer.company),
                    title=offer.title,
                    description=execution_note or offer.description,
                    planned_start=planned_start,
                    planned_end=planned_end,
                    employees_count=len(assigned_employees) or offer.employees_count,
                    labor_hours=offer.labor_hours or Decimal("0"),
                    execution_days=offer.execution_days or 0,
                    total_netto=total_netto,
                    total_brutto=total_brutto,
                    created_by=request.user,
                )

                work_order.assigned_employees.set(assigned_employees)

                WorkActivity.objects.create(
                    company=work_order.company,
                    work=work_order,
                    type=WorkActivity.Type.SYSTEM,
                    title="Utworzono pracę",
                    description=(
                        f"Praca utworzona z oferty: {offer.number}\n"
                        f"Warianty: {', '.join(v.name for v in selected_variants)}"
                    ),
                    created_by=request.user,
                )

                if assigned_employees:
                    WorkActivity.objects.create(
                        company=work_order.company,
                        work=work_order,
                        type=WorkActivity.Type.WORKERS,
                        title="Przypisano pracowników",
                        description=", ".join(
                            u.get_full_name() or u.email
                            for u in assigned_employees
                        ),
                        created_by=request.user,
                    )

                if planned_start or planned_end:
                    WorkActivity.objects.create(
                        company=work_order.company,
                        work=work_order,
                        type=WorkActivity.Type.SCHEDULE,
                        title="Ustawiono termin realizacji",
                        description=(
                            f"Start: {planned_start or '—'}\n"
                            f"Koniec: {planned_end or '—'}"
                        ),
                        created_by=request.user,
                    )

                offer.status = Offer.STATUS_PRZEKAZANE
                offer.forwarded_to_execution_at = timezone.now().date()
                offer.save(update_fields=["status", "forwarded_to_execution_at"])

                OfferActivity.objects.create(
                    company=offer.company,
                    offer=offer,
                    type=OfferActivity.Type.SYSTEM,
                    title="Przekazano ofertę do realizacji",
                    description=f"Utworzono pracę: {work_order.number}",
                    created_by=request.user,
                )

        except Exception as e:
            messages.error(request, f"Nie udało się przekazać oferty do realizacji: {e}")
            return redirect("offer_detail", pk=offer.pk)

        messages.success(
            request,
            f"Oferta została przekazana do realizacji. Utworzono: {work_order.number}"
        )
        return redirect("offer_detail", pk=offer.pk)
