# app/obsluga/views/service_contract_create_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView

from app.obsluga.forms import ServiceContractForm
from app.obsluga.models import (
    ServiceContract,
    ServiceContractMedia,
    ServiceContractMediaType,
    ServiceContractActivity,
    ServiceContractActivityType,
)
from app.dokument.models import DocumentFolder
from app.obsluga.permissions import can_add_obsluga
from django.core.exceptions import PermissionDenied


class ServiceContractCreateView(LoginRequiredMixin, CreateView):
    model = ServiceContract
    form_class = ServiceContractForm
    template_name = "app/obsluga/add.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_add_obsluga(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        contract = form.save(commit=False)
        contract.company = self.request.user.company
        contract.created_by = self.request.user
        contract.save()

        obsluga_folder, _ = DocumentFolder.objects.get_or_create(
            company=self.request.user.company,
            name="Obsługa",
            parent=None,
        )

        ServiceContractActivity.objects.create(
            contract=contract,
            activity_type=ServiceContractActivityType.CREATED,
            message=f"Utworzono obsługę: {contract.title}",
            created_by=self.request.user,
        )

        for image in self.request.FILES.getlist("images"):
            ServiceContractMedia.objects.create(
                contract=contract,
                folder=obsluga_folder,
                file=image,
                media_type=ServiceContractMediaType.IMAGE,
                title=image.name,
                uploaded_by=self.request.user,
            )

            ServiceContractActivity.objects.create(
                contract=contract,
                activity_type=ServiceContractActivityType.FILE_ADDED,
                message=f"Dodano zdjęcie: {image.name}",
                created_by=self.request.user,
            )

        for attachment in self.request.FILES.getlist("attachments"):
            ServiceContractMedia.objects.create(
                contract=contract,
                folder=obsluga_folder,
                file=attachment,
                media_type=ServiceContractMediaType.FILE,
                title=attachment.name,
                uploaded_by=self.request.user,
            )

            ServiceContractActivity.objects.create(
                contract=contract,
                activity_type=ServiceContractActivityType.FILE_ADDED,
                message=f"Dodano plik: {attachment.name}",
                created_by=self.request.user,
            )

        messages.success(
            self.request,
            "Obsługa została dodana."
        )

        return redirect(
            "service_contract_detail",
            pk=contract.pk,
        )
