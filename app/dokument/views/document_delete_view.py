from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.dokument.models import Document


class DocumentDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        document = get_object_or_404(
            Document,
            pk=pk,
            company=request.user.company,
        )

        document_name = document.name

        if document.file:
            document.file.delete(save=False)

        document.delete()

        messages.success(
            request,
            f"Dokument „{document_name}” został usunięty."
        )

        return redirect("documents_list")