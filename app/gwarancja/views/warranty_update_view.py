from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from app.dokument.models import DocumentFolder

from app.gwarancja.forms import WarrantyClaimForm
from app.gwarancja.models import (
    WarrantyClaim,
    WarrantyClaimAttachment,
    WarrantyClaimActivityType,
)
from app.gwarancja.permissions import can_edit_warranty
from django.core.exceptions import PermissionDenied


class WarrantyClaimUpdateView(LoginRequiredMixin, UpdateView):
    model = WarrantyClaim
    form_class = WarrantyClaimForm
    template_name = "app/gwarancja/warranty_claim_create.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_edit_warranty(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return WarrantyClaim.objects.filter(
            company=self.request.user.company
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)

        gwarancje_folder, _ = DocumentFolder.objects.get_or_create(
            company=self.request.user.company,
            name="Gwarancje",
            parent=None,
        )

        self.object.add_activity(
            type=WarrantyClaimActivityType.UPDATED,
            title="Zaktualizowano zgłoszenie",
            description="Zmieniono dane zgłoszenia gwarancyjnego.",
            user=self.request.user,
        )

        for image in form.cleaned_data.get("images", []):
            attachment = WarrantyClaimAttachment.objects.create(
                claim=self.object,
                folder=gwarancje_folder,
                file=image,
                original_name=image.name,
                uploaded_by=self.request.user,
            )

            self.object.add_activity(
                type=WarrantyClaimActivityType.FILE,
                title="Dodano załącznik",
                description=attachment.original_name or attachment.file.name,
                user=self.request.user,
            )

        return response

    def get_success_url(self):
        return reverse_lazy("warranty_detail", kwargs={"pk": self.object.pk})
