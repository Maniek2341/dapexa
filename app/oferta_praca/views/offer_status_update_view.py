from django.views import View
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from decimal import Decimal

from app.oferta_praca.models import Offer, OfferActivity
from app.praca.models import WorkOrder


class OfferStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        offer = get_object_or_404(
            Offer,
            pk=pk,
            company=request.user.company,
        )

        old_status = offer.status
        status = request.POST.get("status")

        try:
            status = int(status)
        except (TypeError, ValueError):
            messages.error(request, "Nieprawidłowy status.")
            return redirect("offer_detail", pk=offer.pk)

        allowed_statuses = dict(Offer.STATUS_CHOICES)

        if status not in allowed_statuses:
            messages.error(request, "Nieprawidłowy status.")
            return redirect("offer_detail", pk=offer.pk)

        # Status „Przekazane do realizacji” może zostać nadany wyłącznie przez
        # przepływ, który atomowo tworzy powiązaną pracę. Zapobiega to sytuacji,
        # w której oferta wygląda na przekazaną, ale nie ma zlecenia w module prac.
        if status == Offer.STATUS_PRZEKAZANE:
            if not WorkOrder.objects.filter(offer=offer, company=offer.company).exists():
                messages.error(
                    request,
                    "Użyj przycisku „Przekaż do realizacji” — najpierw zostanie utworzona praca.",
                )
                return redirect("offer_detail", pk=offer.pk)

        update_fields = ["status"]
        activity_description_extra = ""

        if status == Offer.STATUS_NIEAKTUALNE:
            rejection_reason = (request.POST.get("rejection_reason") or "").strip()

            if not rejection_reason:
                messages.error(request, "Uzupełnij powód odrzucenia oferty.")
                return redirect("offer_detail", pk=offer.pk)

            offer.rejection_reason = rejection_reason
            update_fields.append("rejection_reason")
            activity_description_extra = f"\nPowód: {rejection_reason}"

        if status == Offer.STATUS_PRZYGOTOWANE:
            if not offer.variants.exists():
                messages.error(request, "Dodaj przynajmniej jeden wariant.")
                return redirect("offer_detail", pk=offer.pk)

            try:
                employees_count = int(request.POST.get("employees_count") or 0)
                labor_hours = Decimal(request.POST.get("labor_hours") or "0")
                execution_days = int(request.POST.get("execution_days") or 0)
            except Exception:
                messages.error(request, "Nieprawidłowe wartości.")
                return redirect("offer_detail", pk=offer.pk)

            if employees_count <= 0:
                messages.error(request, "Podaj liczbę pracowników.")
                return redirect("offer_detail", pk=offer.pk)

            if labor_hours <= 0:
                messages.error(request, "Podaj liczbę roboczogodzin.")
                return redirect("offer_detail", pk=offer.pk)

            if execution_days <= 0:
                messages.error(request, "Podaj ilość dni.")
                return redirect("offer_detail", pk=offer.pk)

            offer.employees_count = employees_count
            offer.labor_hours = labor_hours
            offer.execution_days = execution_days

            update_fields += ["employees_count", "labor_hours", "execution_days"]
            activity_description_extra = (
                f"\nPracowników: {employees_count}"
                f"\nRoboczogodziny: {labor_hours}"
                f"\nDni na wykonanie: {execution_days}"
            )

        if status == Offer.STATUS_WYSLANE:
            if not offer.variants.filter(is_selected=True).exists():
                messages.error(
                    request,
                    "Aby ustawić status „Wysłane”, musi być wybrany przynajmniej jeden wariant."
                )
                return redirect("offer_detail", pk=offer.pk)

        if status == Offer.STATUS_SPOTKANIE:
            meeting_date_raw = request.POST.get("meeting_date")

            if not meeting_date_raw:
                messages.error(request, "Podaj datę spotkania.")
                return redirect("offer_detail", pk=offer.pk)

            meeting_date = parse_datetime(meeting_date_raw)

            if meeting_date is None:
                messages.error(request, "Nieprawidłowa data spotkania.")
                return redirect("offer_detail", pk=offer.pk)

            if timezone.is_naive(meeting_date):
                meeting_date = timezone.make_aware(meeting_date)

            offer.meeting_date = meeting_date
            update_fields.append("meeting_date")
            activity_description_extra = f"\nData spotkania: {meeting_date.strftime('%d.%m.%Y %H:%M')}"

        if status == Offer.STATUS_DOZROBIENIA and offer.meeting_date:
            post_meeting_notes = (request.POST.get("post_meeting_notes") or "").strip()

            if not post_meeting_notes:
                messages.error(request, "Uzupełnij informacje po spotkaniu.")
                return redirect("offer_detail", pk=offer.pk)

            offer.post_meeting_notes = post_meeting_notes
            update_fields.append("post_meeting_notes")
            activity_description_extra = f"\nInformacje po spotkaniu:\n{post_meeting_notes}"

        offer.status = status
        offer.save(update_fields=update_fields)

        OfferActivity.objects.create(
            company=offer.company,
            offer=offer,
            type=OfferActivity.Type.STATUS,
            title="Zmieniono status oferty",
            description=(
                f"{allowed_statuses.get(old_status, old_status)} → "
                f"{allowed_statuses.get(status, status)}"
                f"{activity_description_extra}"
            ),
            created_by=request.user,
        )

        messages.success(request, "Status oferty został zmieniony.")
        return redirect("offer_detail", pk=offer.pk)
