# app/obsluga/views/service_contract_parameter_create_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.obsluga.forms import ServiceContractParameterForm
from app.obsluga.models import (
    ServiceContract,
    ServiceContractActivity,
    ServiceContractActivityType,
)


class ServiceContractParameterCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        contract = get_object_or_404(
            ServiceContract,
            pk=pk,
            company=request.user.company,
        )

        form = ServiceContractParameterForm(request.POST)

        if form.is_valid():
            parameter = form.save(commit=False)
            parameter.contract = contract
            parameter.save()

            ServiceContractActivity.objects.create(
                contract=contract,
                activity_type=ServiceContractActivityType.PARAMETER_ADDED,
                message=f"Dodano parametr: {parameter.name} = {parameter.value} {parameter.unit}".strip(),
                created_by=request.user,
            )

            messages.success(
                request,
                "Parametr został dodany."
            )
        else:
            messages.error(
                request,
                "Nie udało się dodać parametru. Sprawdź formularz."
            )

        return redirect(
            "service_contract_detail",
            pk=contract.pk,
        )