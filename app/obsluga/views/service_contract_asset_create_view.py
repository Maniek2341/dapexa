# app/obsluga/views/service_contract_asset_create_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.obsluga.forms import ServiceContractAssetForm
from app.obsluga.models import (
    ServiceContract,
    ServiceContractActivity,
    ServiceContractActivityType,
)


class ServiceContractAssetCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        contract = get_object_or_404(
            ServiceContract,
            pk=pk,
            company=request.user.company,
        )

        form = ServiceContractAssetForm(request.POST)

        if form.is_valid():
            asset = form.save(commit=False)
            asset.contract = contract
            asset.save()

            ServiceContractActivity.objects.create(
                contract=contract,
                activity_type=ServiceContractActivityType.ASSET_ADDED,
                message=f"Dodano element instalacji: {asset.name}",
                created_by=request.user,
            )

            messages.success(
                request,
                "Element instalacji został dodany."
            )
        else:
            messages.error(
                request,
                "Nie udało się dodać elementu. Sprawdź formularz."
            )

        return redirect(
            "service_contract_detail",
            pk=contract.pk,
        )