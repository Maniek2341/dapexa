from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from app.dokument.models import Document


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "app/dokument/list.html"
    context_object_name = "documents"
    paginate_by = 20

    def get_queryset(self):
        return (
            Document.objects
            .filter(company=self.request.user.company)
            .select_related("folder", "uploaded_by")
            .order_by("-created_at")
        )