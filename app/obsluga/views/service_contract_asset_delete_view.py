from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.obsluga.models import (
    ServiceContract,
    ServiceContractAsset,
    ServiceContractActivity,
    ServiceContractActivityType,
)


class ServiceContractAssetDeleteView(LoginRequiredMixin, View):
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

        asset_name = asset.name

        asset.delete()

        ServiceContractActivity.objects.create(
            contract=contract,
            activity_type=ServiceContractActivityType.ASSET_DELETED,
            message=f"Usunięto element instalacji: {asset_name}",
            created_by=request.user,
        )

        messages.success(
            request,
            "Element instalacji został usunięty."
        )

        return redirect(
            "service_contract_detail",
            pk=contract.pk,
        )