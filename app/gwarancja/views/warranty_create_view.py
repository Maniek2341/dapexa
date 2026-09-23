from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

from app.dokument.models import DocumentFolder

from app.gwarancja.models import (
    WarrantyClaim,
    WarrantyClaimAttachment,
    WarrantyClaimActivityType,
)
from app.gwarancja.forms import WarrantyClaimForm


class WarrantyClaimCreateView(LoginRequiredMixin, CreateView):
    model = WarrantyClaim
    form_class = WarrantyClaimForm
    template_name = "app/gwarancja/warranty_claim_create.html"
    success_url = reverse_lazy("warranty_claim_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        form.instance.created_by = self.request.user

        response = super().form_valid(form)

        gwarancje_folder, _ = DocumentFolder.objects.get_or_create(
            company=self.request.user.company,
            name="Gwarancje",
            parent=None,
        )

        self.object.add_activity(
            type=WarrantyClaimActivityType.CREATED,
            title="Utworzono zgłoszenie gwarancyjne",
            description="Dodano nowe zgłoszenie gwarancyjne.",
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