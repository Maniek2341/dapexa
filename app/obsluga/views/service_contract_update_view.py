from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import UpdateView

from app.obsluga.forms import ServiceContractForm
from app.obsluga.models import (
    ServiceContract,
    ServiceContractMedia,
    ServiceContractMediaType,
    ServiceContractActivity,
    ServiceContractActivityType,
)
from app.dokument.models import DocumentFolder
from app.obsluga.permissions import can_edit_obsluga
from django.core.exceptions import PermissionDenied


class ServiceContractUpdateView(LoginRequiredMixin, UpdateView):
    model = ServiceContract
    form_class = ServiceContractForm
    template_name = "app/obsluga/add.html"
    context_object_name = "contract"

    def dispatch(self, request, *args, **kwargs):
        if not can_edit_obsluga(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return ServiceContract.objects.filter(
            company=self.request.user.company
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_title = self.object.title

        self.object = form.save()

        obsluga_folder, _ = DocumentFolder.objects.get_or_create(
            company=self.request.user.company,
            name="Obsługa",
            parent=None,
        )

        ServiceContractActivity.objects.create(
            contract=self.object,
            activity_type=ServiceContractActivityType.UPDATED,
            message=f"Zaktualizowano obsługę: {old_title} → {self.object.title}",
            created_by=self.request.user,
        )

        for image in self.request.FILES.getlist("images"):
            ServiceContractMedia.objects.create(
                contract=self.object,
                folder=obsluga_folder,
                file=image,
                media_type=ServiceContractMediaType.IMAGE,
                title=image.name,
                uploaded_by=self.request.user,
            )

            ServiceContractActivity.objects.create(
                contract=self.object,
                activity_type=ServiceContractActivityType.MEDIA_ADDED,
                message=f"Dodano zdjęcie: {image.name}",
                created_by=self.request.user,
            )

        for attachment in self.request.FILES.getlist("attachments"):
            ServiceContractMedia.objects.create(
                contract=self.object,
                folder=obsluga_folder,
                file=attachment,
                media_type=ServiceContractMediaType.FILE,
                title=attachment.name,
                uploaded_by=self.request.user,
            )

            ServiceContractActivity.objects.create(
                contract=self.object,
                activity_type=ServiceContractActivityType.MEDIA_ADDED,
                message=f"Dodano plik: {attachment.name}",
                created_by=self.request.user,
            )

        messages.success(
            self.request,
            "Obsługa została zaktualizowana."
        )

        return redirect(
            "service_contract_detail",
            pk=self.object.pk
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.object
        return context
