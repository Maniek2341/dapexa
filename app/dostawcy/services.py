import ipaddress
import socket
from itertools import islice
from urllib.parse import urlparse

import requests
from django.db import transaction
from django.utils import timezone

from .adapters import adapter_for
from .models import SupplierCompanyProduct, SupplierIntegration, SupplierProduct

BATCH_SIZE = 500
CONNECT_TIMEOUT = 8
READ_TIMEOUT = 90


class UnsafeFeedError(ValueError):
    pass


class SanitizedFeedError(Exception):
    """An exception safe to persist or send to Celery logs."""


class SanitizedFeedRequestError(requests.RequestException):
    """Retryable request error without provider URL, credentials, or query string."""


def _check_feed_target(url):
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeFeedError("Feed musi używać adresu HTTP lub HTTPS.")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise UnsafeFeedError("Adres feedu wskazuje niedozwolony host.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))}
    except OSError as exc:
        raise requests.ConnectionError("Nie można rozwiązać hosta feedu.") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise UnsafeFeedError("Adres feedu wskazuje niedozwoloną sieć.")


def _chunks(records, size=BATCH_SIZE):
    iterator = iter(records)
    while chunk := list(islice(iterator, size)):
        yield chunk


def _upsert_chunk(integration, records, sync_time, sync_options):
    # A feed may repeat a SKU within one batch. Keep the last row so Postgres
    # ON CONFLICT never tries to update the same target twice in one statement.
    records_by_id = {record.external_id: record for record in records}
    records = list(records_by_id.values())
    supplier = integration.supplier
    external_ids = [record.external_id for record in records]
    existing_ids = set(SupplierProduct.objects.filter(
        supplier=supplier, external_id__in=external_ids
    ).values_list("external_id", flat=True))

    catalog_rows = []
    for row in records:
        if sync_options["catalog"]:
            catalog_rows.append(SupplierProduct(
                supplier=supplier, external_id=row.external_id, sku=row.sku, ean=row.ean,
                name=row.name, manufacturer=row.manufacturer, description=row.description,
                unit=row.unit, vat=row.vat, image_url=row.image_url, product_url=row.product_url,
                metadata=row.metadata,
            ))
    if catalog_rows:
        SupplierProduct.objects.bulk_create(
            catalog_rows, batch_size=BATCH_SIZE, update_conflicts=True,
            unique_fields=["supplier", "external_id"],
            update_fields=["sku", "ean", "name", "manufacturer", "description", "unit", "vat", "image_url", "product_url", "metadata", "updated_at"],
        )

    products = {
        product.external_id: product
        for product in SupplierProduct.objects.filter(
            supplier=supplier, external_id__in=external_ids
        )
    }
    existing_links = {
        row.supplier_product_id: row
        for row in SupplierCompanyProduct.objects.filter(
            integration=integration, supplier_product_id__in=[product.pk for product in products.values()]
        )
    }
    company_rows = []
    for row in records:
        product = products.get(row.external_id)
        if product is None:
            continue
        values = {"integration": integration, "supplier_product": product, "company": integration.company}
        existing = existing_links.get(product.pk)
        if sync_options["prices"] and row.purchase_price_net is not None:
            values["purchase_price_net"] = row.purchase_price_net
        elif existing:
            values["purchase_price_net"] = existing.purchase_price_net
        if sync_options["stock"] and row.stock_quantity is not None:
            values["stock_quantity"] = row.stock_quantity
        elif existing:
            values["stock_quantity"] = existing.stock_quantity
        if sync_options["stock"] and row.availability is not None:
            values["availability"] = row.availability
        elif existing:
            values["availability"] = existing.availability
        company_rows.append(SupplierCompanyProduct(**values, last_sync_at=sync_time))
    if company_rows:
        update_fields = ["last_sync_at"]
        if sync_options["prices"]:
            update_fields.append("purchase_price_net")
        if sync_options["stock"]:
            update_fields.extend(["stock_quantity", "availability"])
        SupplierCompanyProduct.objects.bulk_create(
            company_rows, batch_size=BATCH_SIZE, update_conflicts=True,
            unique_fields=["integration", "supplier_product"], update_fields=update_fields,
        )
    added = sum(1 for external_id in external_ids if external_id not in existing_ids) if sync_options["catalog"] else 0
    return added, max(0, len(records) - added)


def sync_integration(integration_id, components=None):
    """Stream and synchronize one integration; no source feed is persisted."""
    integration = SupplierIntegration.objects.select_related("supplier", "company").get(pk=integration_id)
    if not integration.is_active:
        raise ValueError("Integracja jest nieaktywna.")
    sync_time = timezone.now()
    allowed_components = {"catalog", "prices", "stock"}
    if components is not None and (not components or not set(components) <= allowed_components):
        raise ValueError("Nieprawidłowy typ synchronizacji.")
    requested = set(components or allowed_components)
    sync_options = {
        "catalog": integration.sync_catalog and "catalog" in requested,
        "prices": integration.sync_prices and "prices" in requested,
        "stock": integration.sync_stock and "stock" in requested,
    }
    integration.last_sync_status = SupplierIntegration.SyncStatus.RUNNING
    integration.last_sync_error = ""
    integration.save(update_fields=["last_sync_status", "last_sync_error", "updated_at"])
    processed = added = updated = errors = 0
    try:
        _check_feed_target(integration.feed_url)
        # Redirects are disabled so the configured host cannot redirect the worker to an internal service.
        with requests.get(
            integration.feed_url,
            stream=True,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            allow_redirects=False,
            headers={"User-Agent": "Dapexa-SupplierSync/1.0"},
        ) as response:
            if 300 <= response.status_code < 400:
                raise UnsafeFeedError("Feed przekierowuje na inny adres.")
            response.raise_for_status()
            response.raw.decode_content = True
            adapter = adapter_for(integration.supplier.slug, integration.settings.get("mapping", {}))
            if integration.feed_type == SupplierIntegration.FeedType.XML:
                records = adapter.parse_xml(response.raw)
            else:
                records = adapter.parse_csv_lines(response.iter_lines(decode_unicode=True))
            for chunk in _chunks(records):
                try:
                    with transaction.atomic():
                        batch_added, batch_updated = _upsert_chunk(integration, chunk, sync_time, sync_options)
                except Exception:
                    errors += len(chunk)
                    raise
                processed += len(chunk)
                added += batch_added
                updated += batch_updated
            errors += adapter.parse_errors
        status = SupplierIntegration.SyncStatus.PARTIAL if errors else SupplierIntegration.SyncStatus.SUCCESS
        return _finish(integration, sync_time, status, processed, added, updated, errors, "")
    except Exception as exc:
        # Exception text can contain the complete signed feed URL; never persist it.
        safe_message = "Nie udało się pobrać lub przetworzyć feedu. Sprawdź konfigurację i format pliku."
        status = SupplierIntegration.SyncStatus.PARTIAL if processed else SupplierIntegration.SyncStatus.ERROR
        _finish(integration, sync_time, status, processed, added, updated, errors, safe_message)
        if isinstance(exc, requests.RequestException):
            raise SanitizedFeedRequestError("Błąd połączenia z feedem dostawcy.") from None
        raise SanitizedFeedError(safe_message) from None


def _finish(integration, sync_time, status, processed, added, updated, errors, error):
    SupplierIntegration.objects.filter(pk=integration.pk).update(
        last_sync_at=sync_time,
        last_sync_status=status,
        last_sync_error=error,
        last_sync_processed=processed,
        last_sync_added=added,
        last_sync_updated=updated,
        last_sync_errors=errors,
        updated_at=timezone.now(),
    )
