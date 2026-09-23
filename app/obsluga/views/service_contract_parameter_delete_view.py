from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.obsluga.models import (
    ServiceContract,
    ServiceContractParameter,
    ServiceContractActivity,
    ServiceContractActivityType,
)


class ServiceContractParameterDeleteView(LoginRequiredMixin, View):
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

        parameter_name = parameter.name
        parameter_value = parameter.value
        parameter_unit = parameter.unit or ""

        parameter.delete()

        ServiceContractActivity.objects.create(
            contract=contract,
            activity_type=ServiceContractActivityType.PARAMETER_DELETED,
            message=f"Usunięto parametr: {parameter_name} = {parameter_value} {parameter_unit}".strip(),
            created_by=request.user,
        )

        messages.success(
            request,
            "Parametr został usunięty."
        )

        return redirect(
            "service_contract_detail",
            pk=contract.pk,
        )