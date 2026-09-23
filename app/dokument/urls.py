from django.urls import path
from app.dokument.views import DocumentCreateView, DocumentListView, DocumentDeleteView, DocumentUpdateView

urlpatterns = [
    path("add/", DocumentCreateView.as_view(), name="document_add"),
    path("", DocumentListView.as_view(), name="documents_list"),
    path("<int:pk>/delete/", DocumentDeleteView.as_view(), name="document_delete"),
    path("<int:pk>/edit/", DocumentUpdateView.as_view(), name="document_edit"),
]