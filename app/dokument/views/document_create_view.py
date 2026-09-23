from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView

from app.dokument.forms import DocumentCreateForm
from app.dokument.models import Document, DocumentFolder


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentCreateForm
    template_name = "app/dokument/add.html"
    success_url = reverse_lazy("documents_list")

    def form_valid(self, form):
        dokumenty_folder, _ = DocumentFolder.objects.get_or_create(
            company=self.request.user.company,
            name="Dokumenty",
            parent=None,
        )

        form.instance.company = self.request.user.company
        form.instance.uploaded_by = self.request.user
        form.instance.folder = dokumenty_folder

        messages.success(self.request, "Dokument został dodany.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Popraw błędy w formularzu.")
        return super().form_invalid(form)