from io import BytesIO
from unittest.mock import Mock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase
from django.test import RequestFactory
from django.urls import reverse

from app.core.auth_backends import RoleViewPermissionBackend
from app.core.models import Company, PanelUser, Subscription
from app.dostawcy.adapters import HurtonAdapter, OnninenAdapter
from app.dostawcy.forms import SupplierIntegrationForm
from app.dostawcy.models import Supplier, SupplierCompanyProduct, SupplierIntegration, SupplierProduct
from app.dostawcy.services import sync_integration
from app.dostawcy import views
from app.urzadzenie.models import Product


class SupplierIntegrationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma A")
        self.other_company = Company.objects.create(name="Firma B")
        Subscription.objects.create(
            company=self.company, status=Subscription.STATUS_ACTIVE,
            package=Subscription.Package.STANDARD,
        )
        Subscription.objects.create(
            company=self.other_company, status=Subscription.STATUS_ACTIVE,
            package=Subscription.Package.STANDARD,
        )
        self.supplier = Supplier.objects.get(slug="hurton")
        self.integration = SupplierIntegration.objects.create(
            company=self.company, supplier=self.supplier, name="Feed Hurton",
            feed_url="https://feed.example.test/private?token=super-secret", is_active=True,
        )
        self.user = PanelUser.objects.create_user(
            email="owner@example.test", password="Test-password-12345", company=self.company,
            role=PanelUser.Role.OWNER,
        )
        self.request_factory = RequestFactory()

    def request_as(self, user, method="get", path="/"):
        request = getattr(self.request_factory, method)(path)
        request.user = user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_company_isolation_in_catalog(self):
        product = SupplierProduct.objects.create(
            supplier=self.supplier, external_id="x1", sku="X1", name="Produkt wspólny"
        )
        SupplierCompanyProduct.objects.create(
            company=self.company, integration=self.integration, supplier_product=product,
            purchase_price_net="10.50", stock_quantity="3",
        )
        response = views.supplier_catalog(self.request_as(self.user, path=reverse("supplier_catalog")))
        self.assertContains(response, "Produkt wspólny")

        other_user = PanelUser.objects.create_user(
            email="owner-b@example.test", password="Test-password-12345", company=self.other_company,
            role=PanelUser.Role.OWNER,
        )
        response = views.supplier_catalog(self.request_as(other_user, path=reverse("supplier_catalog")))
        self.assertNotContains(response, "Produkt wspólny")

    def test_integration_creation_encrypts_feed_url(self):
        integration = SupplierIntegration.objects.create(
            company=self.other_company, supplier=Supplier.objects.get(slug="onninen"),
            name="Onninen", feed_url="https://feed.example.test/?key=hidden",
        )
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT feed_url FROM dostawcy_supplierintegration WHERE id = %s", [integration.pk])
            stored = cursor.fetchone()[0]
        self.assertNotIn("hidden", stored)
        self.assertEqual(integration.feed_url, "https://feed.example.test/?key=hidden")
        rendered = str(SupplierIntegrationForm(instance=integration))
        self.assertNotIn("key=hidden", rendered)

    def test_integration_settings_page_does_not_render_saved_feed_url(self):
        response = views.integration_detail(
            self.request_as(self.user, path=reverse("supplier_integration_detail", args=["hurton"])),
            "hurton",
        )
        self.assertContains(response, "Synchronizacja")
        self.assertNotContains(response, "super-secret")
        self.assertNotContains(response, "feed.example.test")

    def test_integration_list_renders_provider_cards(self):
        response = views.integration_list(
            self.request_as(self.user, path=reverse("supplier_integrations"))
        )
        self.assertContains(response, "Hurton")
        self.assertContains(response, "Onninen")

    def test_invalid_post_does_not_echo_submitted_feed_token(self):
        form = SupplierIntegrationForm(data={
            "name": "", "feed_url": "https://feed.example.test/?token=do-not-show",
            "feed_type": "xml",
        }, instance=self.integration)
        self.assertFalse(form.is_valid())
        self.assertNotIn("do-not-show", str(form))

    @patch("app.dostawcy.services._check_feed_target")
    @patch("app.dostawcy.services.requests.get")
    def test_sync_creates_catalog_and_company_price_stock(self, get, _check):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status_code = 200
        response.raise_for_status = Mock()
        response.raw = BytesIO(b'<feed><product><id>sku-1</id><sku>SKU-1</sku><name>Pompa</name><price_net>12.30</price_net><stock>4</stock></product></feed>')
        get.return_value = response
        result = sync_integration(self.integration.pk)
        self.assertEqual(result, None)
        self.assertEqual(SupplierProduct.objects.filter(supplier=self.supplier).count(), 1)
        company_row = SupplierCompanyProduct.objects.get(company=self.company)
        self.assertEqual(str(company_row.purchase_price_net), "12.3000")
        self.assertEqual(str(company_row.stock_quantity), "4.000")

    @patch("app.dostawcy.services._check_feed_target")
    @patch("app.dostawcy.services.requests.get")
    def test_resync_updates_existing_row_without_duplicate(self, get, _check):
        def fake_response(price, stock):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status_code = 200
            response.raise_for_status = Mock()
            response.raw = BytesIO(f'<feed><product><id>one</id><name>Product</name><price_net>{price}</price_net><stock>{stock}</stock></product></feed>'.encode())
            return response
        get.side_effect = [fake_response("10", "2"), fake_response("15", "8")]
        sync_integration(self.integration.pk)
        sync_integration(self.integration.pk)
        self.assertEqual(SupplierProduct.objects.filter(supplier=self.supplier).count(), 1)
        row = SupplierCompanyProduct.objects.get(company=self.company)
        self.assertEqual(str(row.purchase_price_net), "15.0000")
        self.assertEqual(str(row.stock_quantity), "8.000")

    @patch("app.dostawcy.services._check_feed_target")
    @patch("app.dostawcy.services.requests.get")
    def test_component_sync_updates_only_selected_data(self, get, _check):
        supplier_product = SupplierProduct.objects.create(
            supplier=self.supplier, external_id="one", name="Old name", sku="one"
        )
        company_row = SupplierCompanyProduct.objects.create(
            company=self.company, integration=self.integration, supplier_product=supplier_product,
            purchase_price_net="10", stock_quantity="2",
        )
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status_code = 200
        response.raise_for_status = Mock()
        response.raw = BytesIO(b'<feed><product><id>one</id><name>New name</name><price_net>20</price_net><stock>9</stock></product></feed>')
        get.return_value = response
        sync_integration(self.integration.pk, components=["prices"])
        supplier_product.refresh_from_db()
        company_row.refresh_from_db()
        self.assertEqual(supplier_product.name, "Old name")
        self.assertEqual(str(company_row.purchase_price_net), "20.0000")
        self.assertEqual(str(company_row.stock_quantity), "2.000")

    @patch("app.dostawcy.services._check_feed_target")
    @patch("app.dostawcy.services.requests.get", side_effect=OSError("https://user:secret@example.test/?token=x"))
    def test_unavailable_feed_sanitizes_error(self, _get, _check):
        from app.dostawcy.services import SanitizedFeedError
        with self.assertRaises(SanitizedFeedError):
            sync_integration(self.integration.pk)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.last_sync_status, SupplierIntegration.SyncStatus.ERROR)
        self.assertNotIn("secret", self.integration.last_sync_error)
        self.assertNotIn("token", self.integration.last_sync_error)

    @patch("app.dostawcy.services._check_feed_target")
    @patch("app.dostawcy.services.requests.get")
    def test_malformed_feed_is_reported_without_leaking_url(self, get, _check):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status_code = 200
        response.raise_for_status = Mock()
        response.raw = BytesIO(b"<feed><product>")
        get.return_value = response
        from app.dostawcy.services import SanitizedFeedError
        with self.assertRaises(SanitizedFeedError):
            sync_integration(self.integration.pk)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.last_sync_status, SupplierIntegration.SyncStatus.ERROR)
        self.assertNotIn("super-secret", self.integration.last_sync_error)

    def test_xml_parser_streaming(self):
        rows = list(HurtonAdapter().parse_xml(BytesIO(
            b'<feed><product><id>42</id><name>Grzejnik</name><sku>G-42</sku></product></feed>'
        )))
        self.assertEqual((rows[0].external_id, rows[0].name, rows[0].sku), ("42", "Grzejnik", "G-42"))

    def test_csv_parser_and_custom_mapping(self):
        rows = list(OnninenAdapter({"external_id": "kod", "name": "nazwa", "purchase_price_net": "cena"}).parse_csv_lines(
            ["kod,nazwa,cena\n", "A-1,Zawór,22.50\n"]
        ))
        self.assertEqual(rows[0].external_id, "A-1")
        self.assertEqual(str(rows[0].purchase_price_net), "22.50")

    def test_add_supplier_product_creates_company_product_only_on_action(self):
        supplier_product = SupplierProduct.objects.create(
            supplier=self.supplier, external_id="p1", sku="P-1", ean="123", name="Silnik", unit="szt."
        )
        row = SupplierCompanyProduct.objects.create(
            company=self.company, integration=self.integration, supplier_product=supplier_product,
            purchase_price_net="100.00",
        )
        self.assertEqual(Product.objects.filter(company=self.company).count(), 0)
        request = self.request_as(self.user, method="post", path=reverse("supplier_product_add", args=[row.pk]))
        response = views.supplier_product_add(request, row.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.filter(company=self.company).count(), 1)
        row.refresh_from_db()
        self.assertEqual(row.local_product.name, "Silnik")

    def test_other_company_cannot_sync_integration(self):
        other_user = PanelUser.objects.create_user(
            email="other@example.test", password="Test-password-12345", company=self.other_company,
            role=PanelUser.Role.OWNER,
        )
        from django.http import Http404
        request = self.request_as(other_user, method="post", path=reverse("supplier_integration_sync", args=[self.integration.pk]))
        with self.assertRaises(Http404):
            views.integration_sync(request, self.integration.pk)

    def test_supplier_integration_permissions_exist_for_management_roles(self):
        backend = RoleViewPermissionBackend()
        manager = PanelUser(email="manager@example.test", role=PanelUser.Role.MANAGER)
        employee = PanelUser(email="employee@example.test", role=PanelUser.Role.EMPLOYEE)
        self.assertTrue(backend.has_perm(manager, "dostawcy.access_supplier_integration_save"))
        self.assertFalse(backend.has_perm(employee, "dostawcy.access_supplier_integration_save"))
