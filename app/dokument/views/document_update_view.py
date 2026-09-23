from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from app.dokument.forms import DocumentCreateForm
from app.dokument.models import Document


class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentCreateForm
    template_name = "app/dokument/add.html"
    success_url = reverse_lazy("documents_list")

    def get_queryset(self):
        return Document.objects.filter(company=self.request.user.company)

    def form_valid(self, form):
        messages.success(self.request, "Dokument został zaktualizowany.")
        return super().form_valid(form)