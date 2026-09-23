import requests
from django.conf import settings


class GeocodingService:

    @staticmethod
    def get_coordinates(street: str = "", city: str = "", postcode: str = "", country: str = "Polska"):
        street = (street or "").strip()
        city = (city or "").strip()
        postcode = (postcode or "").strip()
        country = (country or "Polska").strip()

        if not city and not street:
            return None, None

        address_query = ", ".join([
            part for part in [
                street,
                f"{postcode} {city}".strip(),
                country,
            ]
            if part
        ])

        url = "https://maps.googleapis.com/maps/api/geocode/json"

        params = {
            "address": address_query,
            "key": settings.GOOGLE_API_KEY,
            "region": "pl",
            "language": "pl",
        }

        try:
            response = requests.get(url, params=params, timeout=8)
            response.raise_for_status()

            data = response.json()
            status = data.get("status")

            if status != "OK":
                print("Google geocode error:", status)
                print("Address query:", address_query)
                print("Google response:", data)
                return None, None

            location = data["results"][0]["geometry"]["location"]

            return location["lat"], location["lng"]

        except Exception as e:
            print("Google Geocoding error:", e)
            print("Address query:", address_query)
            return None, None