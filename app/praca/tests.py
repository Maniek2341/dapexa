from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.messages import get_messages
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.core.models import Company, PanelUser, Subscription
from app.klient.models import Client
from app.oferta_praca.models import Offer, OfferVariant, OfferVariantFile, OfferVariantItem
from app.praca.models import WorkOrder
from app.urzadzenie.models import Product


class WorkPriceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma cen")
        self.owner = PanelUser.objects.create_user(
            email="prices@example.com", password="test-password",
            company=self.company, role=PanelUser.Role.OWNER,
        )
        Subscription.objects.create(
            company=self.company, owner=self.owner,
            package=Subscription.Package.PRO, status=Subscription.STATUS_ACTIVE,
        )
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")
        customer = Client.objects.create(company=self.company, name="Klient")
        self.offer = Offer.objects.create(
            company=self.company, client=customer, number="OF/1", title="Oferta",
            issue_date=timezone.localdate(),
        )
        self.variant = OfferVariant.objects.create(
            company=self.company, offer=self.offer, name="Wariant", is_selected=True,
            source_type=OfferVariant.SourceType.PDF,
            total_netto=Decimal("100"), total_brutto=Decimal("100"),
        )
        OfferVariantFile.objects.create(
            company=self.company, variant=self.variant, file="test/offer.pdf",
        )
        response = self.client.post(reverse("offer_forward_to_execution", args=[self.offer.pk]))
        self.assertTrue(
            WorkOrder.objects.filter(offer=self.offer).exists(),
            (response.status_code, response.get("Location"),
             [str(message) for message in get_messages(response.wsgi_request)]),
        )
        self.work = WorkOrder.objects.get(offer=self.offer)

    def assert_totals(self, netto, brutto):
        self.work.refresh_from_db()
        self.assertEqual(self.work.total_netto, Decimal(netto))
        self.assertEqual(self.work.total_brutto, Decimal(brutto))

    def test_pdf_edit_updates_work_detail_and_list_summary(self):
        response = self.client.post(reverse("offer_variant_edit", args=[self.variant.pk]), {
            "source_type": "pdf", "name": self.variant.name, "is_selected": "on",
            "pdf_total_netto": "350.50", "pdf_materials_netto": "50",
            "pdf_accessories_netto": "20",
        })
        self.assertEqual(response.status_code, 302)
        self.assert_totals("350.50", "350.50")
        detail = self.client.get(reverse("work_detail", args=[self.work.pk]))
        self.assertEqual(detail.context["work"].total_netto, Decimal("350.50"))
        listing = self.client.get(reverse("workorder_list"))
        self.assertEqual(listing.context["work_summary"]["total_netto"], Decimal("350.50"))
        self.assertEqual(listing.context["work_summary"]["profit"], Decimal("280.50"))

    def test_items_edit_recalculates_netto_and_vat(self):
        product = Product.objects.create(
            company=self.company, name="Materiał", net_price=Decimal("100"),
        )
        self.variant.source_type = OfferVariant.SourceType.ITEMS
        self.variant.save()
        item = OfferVariantItem.objects.create(
            company=self.company, variant=self.variant, product=product,
            item_type="material", name=product.name, quantity=2, unit_price_netto=100,
        )
        for price, vat, netto, brutto in [
            ("150.25", "23", "300.50", "369.62"),
            ("150.25", "0", "300.50", "300.50"),
            ("0", "23", "0", "0"),
        ]:
            with self.subTest(price=price, vat=vat):
                response = self.client.post(reverse("offer_variant_edit", args=[self.variant.pk]), {
                    "source_type": "items", "name": self.variant.name, "is_selected": "on",
                    "items-TOTAL_FORMS": "1", "items-INITIAL_FORMS": "1",
                    "items-0-id": item.pk, "items-0-product": product.pk,
                    "items-0-name": product.name, "items-0-item_type": "material",
                    "items-0-quantity": "2", "items-0-unit": "szt.",
                    "items-0-unit_price_netto": price, "items-0-vat_rate": vat,
                })
                self.assertEqual(response.status_code, 302)
                self.assert_totals(netto, brutto)

    def test_selection_and_deletion_sum_only_selected_variants(self):
        second = OfferVariant.objects.create(
            company=self.company, offer=self.offer, name="Drugi", is_selected=True,
            total_netto=Decimal("200"), total_brutto=Decimal("246"),
        )
        OfferVariant.objects.create(
            company=self.company, offer=self.offer, name="Niewybrany",
            total_netto=Decimal("999"), total_brutto=Decimal("999"),
        )
        self.assert_totals("300", "346")
        self.client.post(reverse("offer_variant_toggle_selected", args=[second.pk]))
        self.assert_totals("100", "100")
        self.client.post(reverse("offer_variant_toggle_selected", args=[self.variant.pk]))
        self.assert_totals("0", "0")
        self.client.post(reverse("offer_variant_toggle_selected", args=[second.pk]))
        self.assert_totals("200", "246")
        self.client.post(reverse("offer_variant_delete", args=[second.pk]))
        self.assert_totals("0", "0")

    def test_deleting_last_variant_clears_work_and_summary(self):
        self.client.post(reverse("offer_variant_delete", args=[self.variant.pk]))
        self.assert_totals("0", "0")
        response = self.client.get(reverse("workorder_list"))
        self.assertEqual(response.context["work_summary"]["total_netto"], 0)

    def test_item_deletion_recalculates_work(self):
        self.variant.source_type = OfferVariant.SourceType.ITEMS
        self.variant.save()
        item = OfferVariantItem.objects.create(
            company=self.company, variant=self.variant, item_type="service",
            name="Usługa", quantity=2, unit_price_netto=50, vat_rate=8,
        )
        self.assert_totals("100", "108")
        item.delete()
        self.assert_totals("0", "0")

    def test_unselected_variant_does_not_change_work(self):
        other = OfferVariant.objects.create(
            company=self.company, offer=self.offer, name="Niewybrany",
            total_netto=Decimal("999"), total_brutto=Decimal("999"),
        )
        other.total_netto = Decimal("1234")
        other.save()
        self.assert_totals("100", "100")

    def test_backfill_repairs_stale_totals_and_empty_selection(self):
        migration = import_module("app.praca.migrations.0007_refresh_work_prices")
        WorkOrder.objects.filter(pk=self.work.pk).update(total_netto=999, total_brutto=999)
        migration.refresh_work_prices(apps, SimpleNamespace(connection=connection))
        self.assert_totals("100", "100")
        OfferVariant.objects.filter(pk=self.variant.pk).update(is_selected=False)
        migration.refresh_work_prices(apps, SimpleNamespace(connection=connection))
        self.assert_totals("0", "0")
