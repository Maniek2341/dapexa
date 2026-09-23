from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Company, CompanySettings
from .subscription_lifecycle import _delete_company_files


@receiver(post_save, sender=Company)
def create_company_settings(sender, instance, created, **kwargs):
    if created:
        CompanySettings.objects.create(company=instance)


@receiver(pre_delete, sender=Company)
def delete_company_files_before_delete(sender, instance, **kwargs):
    """Remove uploaded files before Django cascades the company's records."""
    if not getattr(instance, "_company_files_deleted", False):
        _delete_company_files(instance)
        instance._company_files_deleted = True
