from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.obsluga.forms import ServiceContractAssetForm
from app.obsluga.models import (
    ServiceContract,
    ServiceContractAsset,
    ServiceContractActivity,
    ServiceContractActivityType,
)


class ServiceContractAssetUpdateView(LoginRequiredMixin, View):
    def post(self, request, contract_pk, asset_pk):
        contract = get_object_or_404(
            ServiceContract,
            pk=contract_pk,
            company=request.user.company,
        )

        asset = get_object_or_404(
            ServiceContractAsset,
            pk=asset_pk,
            contract=contract,
        )

        old_name = asset.name

        form = ServiceContractAssetForm(
            request.POST,
            instance=asset,
        )

        if form.is_valid():
            asset = form.save()

            ServiceContractActivity.objects.create(
                contract=contract,
                activity_type=ServiceContractActivityType.ASSET_UPDATED,
                message=f"Zaktualizowano element instalacji: {old_name} → {asset.name}",
                created_by=request.user,
            )

            messages.success(request, "Element instalacji został zaktualizowany.")
        else:
            messages.error(request, "Nie udało się zaktualizować elementu.")

        return redirect("service_contract_detail", pk=contract.pk)