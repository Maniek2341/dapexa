from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.obsluga.forms import ServiceContractParameterForm
from app.obsluga.models import (
    ServiceContract,
    ServiceContractParameter,
    ServiceContractActivity,
    ServiceContractActivityType,
)


class ServiceContractParameterUpdateView(LoginRequiredMixin, View):
    def post(self, request, contract_pk, parameter_pk):
        contract = get_object_or_404(
            ServiceContract,
            pk=contract_pk,
            company=request.user.company,
        )

        parameter = get_object_or_404(
            ServiceContractParameter,
            pk=parameter_pk,
            contract=contract,
        )

        old_name = parameter.name
        old_value = parameter.value
        old_unit = parameter.unit or ""

        form = ServiceContractParameterForm(
            request.POST,
            instance=parameter,
        )

        if form.is_valid():
            parameter = form.save()

            ServiceContractActivity.objects.create(
                contract=contract,
                activity_type=ServiceContractActivityType.PARAMETER_UPDATED,
                message=(
                    f"Zaktualizowano parametr: "
                    f"{old_name} = {old_value} {old_unit} → "
                    f"{parameter.name} = {parameter.value} {parameter.unit or ''}"
                ).strip(),
                created_by=request.user,
            )

            messages.success(request, "Parametr został zaktualizowany.")
        else:
            messages.error(request, "Nie udało się zaktualizować parametru.")

        return redirect("service_contract_detail", pk=contract.pk)