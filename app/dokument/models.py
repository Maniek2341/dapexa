# app/documents/models.py
from django.db import models
from app.core.models import CompanyOwnedModel
from app.core.fields import TrackedFileField, file_size_field
from app.core.view_permissions import view_permissions
from django.conf import settings


def company_document_path(instance, filename):
    return f"companies/{instance.company_id}/documents/{filename}"


class DocumentFolder(CompanyOwnedModel):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Folder na dokument'
        verbose_name_plural = 'Folder na dokumenty'


class Document(CompanyOwnedModel):
    name = models.CharField(max_length=255)
    file = TrackedFileField(upload_to=company_document_path)
    file_size = file_size_field()
    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Dokument'
        verbose_name_plural = 'Dokumenty'
        permissions = view_permissions(
            "document_add", "documents_list", "document_delete", "document_edit",
        )
