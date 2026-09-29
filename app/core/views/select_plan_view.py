# app/core/views/views_subscription.py (np.)
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from app.core.models import Subscription


def _display_price(amount):
    value = f"{amount / 100:.2f}".rstrip("0").rstrip(".")
    return f"{value} zł"


@login_required
def select_plan(request):
    company = getattr(request.user, "company", None)
    subscription = None
    if company:
        subscription = company.subscriptions.order_by("-created_at").first()

    packages = [
        {
            "code": Subscription.Package.START,
            "name": "Start",
            "price_monthly": _display_price(settings.STRIPE_PLAN_PRICE_AMOUNTS["start"]["monthly"]) + " / mies.",
            "price_yearly": _display_price(settings.STRIPE_PLAN_PRICE_AMOUNTS["start"]["yearly"]) + " / rok",
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
            "price_monthly": _display_price(settings.STRIPE_PLAN_PRICE_AMOUNTS["standard"]["monthly"]) + " / mies.",
            "price_yearly": _display_price(settings.STRIPE_PLAN_PRICE_AMOUNTS["standard"]["yearly"]) + " / rok",
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
            "price_monthly": _display_price(settings.STRIPE_PLAN_PRICE_AMOUNTS["pro"]["monthly"]) + " / mies.",
            "price_yearly": _display_price(settings.STRIPE_PLAN_PRICE_AMOUNTS["pro"]["yearly"]) + " / rok",
            "features": [
                "Nielimitowana liczba użytkowników",
                "Nielimitowani klienci i protokoły",
                "100 GB przestrzeni na pliki",
                "Pełna automatyzacja procesów",
                "Priorytetowe wsparcie 1:1",
                "Dedykowany opiekun wdrożeniowy",
            ],
        },
    ]
    for package in packages:
        monthly_price_id = settings.STRIPE_PRICE_IDS[package["code"]][Subscription.BILLING_MONTHLY]
        yearly_price_id = settings.STRIPE_PRICE_IDS[package["code"]][Subscription.BILLING_YEARLY]
        if subscription and subscription.stripe_price_id:
            package["current_monthly"] = subscription.stripe_price_id == monthly_price_id
            package["current_yearly"] = subscription.stripe_price_id == yearly_price_id
        else:
            package["current_monthly"] = bool(
                subscription
                and subscription.package == package["code"]
                and subscription.billing_period == Subscription.BILLING_MONTHLY
            )
            package["current_yearly"] = bool(
                subscription
                and subscription.package == package["code"]
                and subscription.billing_period == Subscription.BILLING_YEARLY
            )
        package["is_current"] = package["current_monthly"] or package["current_yearly"]

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
        "packages": packages,
    }
    return render(request, "app/core/select_plan.html", context)
