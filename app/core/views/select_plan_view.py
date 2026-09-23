# app/core/views/views_subscription.py (np.)
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from app.core.models import Subscription


@login_required
def select_plan(request):
    company = getattr(request.user, "company", None)
    subscription = None
    if company:
        subscription = company.subscriptions.order_by("-created_at").first()

    context = {
        "company": company,
        "subscription": subscription,
        "is_existing_subscription": bool(
            subscription
            and subscription.stripe_subscription_id
            and subscription.status in {
                Subscription.STATUS_ACTIVE,
                Subscription.STATUS_TRIALING,
            }
        ),
        "packages": [
            {
                "code": Subscription.Package.START,
                "name": "Start",
                "price_monthly": "100 zł / mies.",
                "price_yearly": "1000 zł / rok",
                "features": [
                    "Podstawowe moduły CRM",
                    "Do 3 użytkowników",
                    "Do 50 klientów i 70 protokołów",
                    "5 GB przestrzeni na pliki",
                    "Podstawowe raporty",
                ],
            },
            {
                "code": Subscription.Package.STANDARD,
                "name": "Standard",
                "price_monthly": "199 zł / mies.",
                "price_yearly": "1990 zł / rok",
                "features": [
                    "Wszystkie moduły serwisowe",
                    "Do 10 użytkowników",
                    "Do 200 klientów i 200 protokołów",
                    "25 GB przestrzeni na pliki",
                    "Zaawansowane raporty i statystyki",
                    "Priorytetowe wsparcie mailowe",
                ],
            },
            {
                "code": Subscription.Package.PRO,
                "name": "Pro",
                "price_monthly": "399 zł / mies.",
                "price_yearly": "3990 zł / rok",
                "features": [
                    "Nielimitowana liczba użytkowników",
                    "Nielimitowani klienci i protokoły",
                    "100 GB przestrzeni na pliki",
                    "Pełna automatyzacja procesów",
                    "Priorytetowe wsparcie 1:1",
                    "Dedykowany opiekun wdrożeniowy",
                ],
            },
        ],
    }
    return render(request, "app/core/select_plan.html", context)
