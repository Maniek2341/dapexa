import requests
from celery import shared_task

from .models import SupplierIntegration
from .services import sync_integration


@shared_task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True,
             retry_kwargs={"max_retries": 3}, name="app.dostawcy.tasks.sync_supplier_integration")
def sync_supplier_integration(self, integration_id, components=None):
    try:
        return sync_integration(integration_id, components=components)
    except requests.RequestException:
        if self.request.retries < self.max_retries:
            SupplierIntegration.objects.filter(pk=integration_id).update(
                last_sync_status=SupplierIntegration.SyncStatus.QUEUED
            )
        raise


@shared_task(name="app.dostawcy.tasks.sync_active_supplier_integrations")
def sync_active_supplier_integrations():
    ids = SupplierIntegration.objects.filter(is_active=True).values_list("id", flat=True)
    queued = 0
    for integration_id in ids:
        SupplierIntegration.objects.filter(pk=integration_id).update(
            last_sync_status=SupplierIntegration.SyncStatus.QUEUED
        )
        sync_supplier_integration.delay(integration_id)
        queued += 1
    return queued
