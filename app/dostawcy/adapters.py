"""Supplier-specific field mapping, separated from transport and persistence.

Hurton and Onninen mappings are intentionally generic until real customer feed
examples are available. Per-integration ``settings.mapping`` overrides them.
"""
import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree


@dataclass
class SupplierRecord:
    external_id: str
    name: str
    sku: str = ""
    ean: str = ""
    manufacturer: str = ""
    description: str = ""
    unit: str = ""
    vat: Decimal | None = None
    image_url: str = ""
    product_url: str = ""
    purchase_price_net: Decimal | None = None
    stock_quantity: Decimal | None = None
    availability: bool | None = None
    metadata: dict = field(default_factory=dict)


DEFAULT_MAPPING = {
    "item_tag": "product",
    "external_id": "id",
    "sku": "sku",
    "ean": "ean",
    "name": "name",
    "manufacturer": "manufacturer",
    "description": "description",
    "unit": "unit",
    "vat": "vat",
    "image_url": "image_url",
    "product_url": "product_url",
    "purchase_price_net": "price_net",
    "stock_quantity": "stock",
    "availability": "available",
}


def _decimal(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).strip().replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _bool(value):
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip().lower() in {"1", "true", "yes", "tak", "dostepny", "available"}


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


class BaseSupplierAdapter:
    slug = ""

    def __init__(self, mapping=None):
        self.mapping = {**DEFAULT_MAPPING, **(mapping or {})}
        self.parse_errors = 0

    def parse_xml(self, binary_stream):
        wanted_tag = self.mapping["item_tag"]
        root = None
        for event, element in ElementTree.iterparse(binary_stream, events=("start", "end")):
            if root is None and event == "start":
                root = element
            if event != "end":
                continue
            if _local_name(element.tag) != wanted_tag:
                continue
            values = {_local_name(child.tag): (child.text or "").strip() for child in element.iter() if child is not element}
            record = self.normalize(values)
            element.clear()
            if root is not None:
                root.clear()
            if record:
                yield record

    def parse_csv_lines(self, lines):
        reader = csv.DictReader((line.decode("utf-8-sig") if isinstance(line, bytes) else line for line in lines))
        for row in reader:
            record = self.normalize(row)
            if record:
                yield record

    def normalize(self, values):
        def get(field_name):
            key = self.mapping.get(field_name, "")
            value = values.get(key, "") if key else ""
            return str(value).strip() if value is not None else ""

        external_id = get("external_id") or get("sku") or get("ean")
        name = get("name")
        if not external_id or not name:
            self.parse_errors += 1
            return None
        availability_raw = get("availability")
        return SupplierRecord(
            external_id=external_id[:255], name=name[:500], sku=get("sku")[:120], ean=get("ean")[:32],
            manufacturer=get("manufacturer")[:255], description=get("description"), unit=get("unit")[:30],
            vat=_decimal(get("vat")), image_url=get("image_url")[:1000], product_url=get("product_url")[:1000],
            purchase_price_net=_decimal(get("purchase_price_net")),
            stock_quantity=_decimal(get("stock_quantity")),
            availability=_bool(availability_raw),
            # Unknown columns stay local to parsing. Feeds may contain contract
            # prices, customer IDs, or other company-specific fields; never copy
            # them into the shared global catalog by default.
            metadata={},
        )


class HurtonAdapter(BaseSupplierAdapter):
    slug = "hurton"


class OnninenAdapter(BaseSupplierAdapter):
    slug = "onninen"


ADAPTERS = {adapter.slug: adapter for adapter in (HurtonAdapter, OnninenAdapter)}


def adapter_for(slug, mapping=None):
    adapter = ADAPTERS.get(slug)
    if adapter is None:
        raise ValueError("Brak adaptera dla wybranego dostawcy.")
    return adapter(mapping=mapping)
