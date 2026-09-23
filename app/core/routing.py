import requests
from decimal import Decimal
from django.conf import settings
from app.core.models import RouteDistanceCache


class RoutingService:

    @staticmethod
    def get_distance(origin, destination):
        """
        origin / destination = Address z latitude / longitude
        """

        if not all([
            origin.latitude,
            origin.longitude,
            destination.latitude,
            destination.longitude
        ]):
            return Decimal("0")

        # 🔥 1️⃣ Sprawdź cache
        cached = RouteDistanceCache.objects.filter(
            origin_lat=origin.latitude,
            origin_lng=origin.longitude,
            dest_lat=destination.latitude,
            dest_lng=destination.longitude
        ).first()

        if cached:
            return cached.distance_km

        # 🔥 2️⃣ Wywołaj ORS
        url = "https://api.openrouteservice.org/v2/directions/driving-car"

        headers = {
            "Authorization": settings.ORS_API_KEY,
            "Content-Type": "application/json"
        }

        body = {
            "coordinates": [
                [origin.longitude, origin.latitude],
                [destination.longitude, destination.latitude]
            ]
        }

        response = requests.post(url, json=body, headers=headers)

        if response.status_code != 200:
            return Decimal("0")

        data = response.json()

        meters = data["routes"][0]["summary"]["distance"]
        km = Decimal(meters) / Decimal("1000")

        # 🔥 3️⃣ Zapisz do cache
        RouteDistanceCache.objects.create(
            origin_lat=origin.latitude,
            origin_lng=origin.longitude,
            dest_lat=destination.latitude,
            dest_lng=destination.longitude,
            distance_km=km
        )

        return km