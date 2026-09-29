from unittest.mock import patch

from django.test import TestCase, override_settings

from app.core.geocoding import GeocodingService
from app.core.models import Address


class OptionalGeocodingTests(TestCase):
    @override_settings(GOOGLE_API_KEY="")
    @patch("app.core.geocoding.requests.get")
    def test_missing_google_key_skips_external_request(self, get):
        self.assertEqual(
            GeocodingService.get_coordinates(street="Main St 1", city="Warszawa"),
            (None, None),
        )
        get.assert_not_called()

    @override_settings(GOOGLE_API_KEY="")
    def test_address_is_saved_without_coordinates_when_geocoding_is_unconfigured(self):
        address = Address.objects.create(
            street="Main St 1",
            postcode="00-001",
            city="Warszawa",
        )

        address.refresh_from_db()
        self.assertIsNone(address.latitude)
        self.assertIsNone(address.longitude)
