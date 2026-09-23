# app/obsluga/views/service_contract_delete_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.obsluga.models import ServiceContract
from app.obsluga.permissions import can_delete_obsluga
from django.core.exceptions import PermissionDenied


class ServiceContractDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not can_delete_obsluga(request.user):
            raise PermissionDenied

        contract = get_object_or_404(
            ServiceContract,
            pk=pk,
            company=request.user.company,
        )

        contract_title = contract.title
        contract.delete()

        messages.success(
            request,
            f"Obsługa „{contract_title}” została usunięta."
        )

        return redirect("service_contract_list")
