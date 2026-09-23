# app/obsluga/views/service_visit_confirm_period_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from app.obsluga.models import (
    ServiceContract,
    ServiceVisit,
    ServiceVisitStatus,
    ServiceContractActivity,
    ServiceContractActivityType,
)

from app.obsluga.services.periods import get_contract_current_period


class ServiceVisitConfirmPeriodView(LoginRequiredMixin, View):
    def post(self, request, pk):
        contract = get_object_or_404(
            ServiceContract,
            pk=pk,
            company=request.user.company,
        )

        period_start, period_end = get_contract_current_period(
            contract,
            today=timezone.localdate(),
        )

        visit, created = ServiceVisit.objects.get_or_create(
            contract=contract,
            period_start=period_start,
            period_end=period_end,
            defaults={
                "title": f"Przegląd okresowy {period_start:%d.%m.%Y} - {period_end:%d.%m.%Y}",
                "status": ServiceVisitStatus.DONE,
                "performed_at": timezone.localdate(),
                "performed_by": request.user,
                "notes": request.POST.get("notes", "").strip(),
                "created_by": request.user,
            },
        )

        if created:
            ServiceContractActivity.objects.create(
                contract=contract,
                activity_type=ServiceContractActivityType.VISIT_CONFIRMED,
                message=(
                    f"Zatwierdzono przegląd okresowy "
                    f"{period_start:%d.%m.%Y} - {period_end:%d.%m.%Y}"
                ),
                created_by=request.user,
            )

            messages.success(
                request,
                "Obsługa została zatwierdzona dla bieżącego okresu."
            )
        else:
            messages.warning(
                request,
                "Ten okres został już zatwierdzony."
            )

        return redirect(
            "service_contract_detail",
            pk=contract.pk,
        )