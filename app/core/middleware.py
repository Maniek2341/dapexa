# app/core/middleware.py
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth import logout
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import resolve, Resolver404, reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from zoneinfo import ZoneInfo
from app.core.models import Subscription
from app.core.view_permissions import PUBLIC_VIEW_NAMES
from app.core.subscription_limits import SubscriptionLimitExceeded


class ViewPermissionMiddleware:
    """Require the custom access_<url_name> permission for company employees."""

    PUBLIC_URL_NAMES = PUBLIC_VIEW_NAMES

    EXEMPT_PREFIXES = ("/static/", "/media/")
    APP_LABEL_OVERRIDES = {"uzytkownik": "core"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.check_permission(request)
        if response:
            return response
        return self.get_response(request)

    def check_permission(self, request):
        if request.path.startswith(self.EXEMPT_PREFIXES):
            return

        try:
            match = resolve(request.path_info)
        except Resolver404:
            return

        user = request.user
        # Dezaktywowany pracownik traci również istniejącą sesję, a nie tylko
        # możliwość rozpoczęcia nowego logowania.
        if user.is_authenticated and not user.is_superuser and (
            not user.is_active
            or not getattr(user, "is_active_employee", True)
        ):
            logout(request)
            if match.url_name in self.PUBLIC_URL_NAMES:
                return
            return redirect_to_login(
                request.get_full_path(),
                login_url=reverse("login"),
            )

        if not match.url_name or match.url_name in self.PUBLIC_URL_NAMES:
            return

        view = getattr(match.func, "view_class", match.func)
        module_parts = getattr(view, "__module__", "").split(".")
        if len(module_parts) < 2 or module_parts[0] != "app":
            return

        if not user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url=reverse("login"),
            )

        if user.is_superuser:
            return

        # Właściciel zarządza prawami, a konta klientów nie są pracownikami.
        if user.role in {user.Role.OWNER, user.Role.CLIENT}:
            return

        app_label = self.APP_LABEL_OVERRIDES.get(module_parts[1], module_parts[1])
        permission_name = f"{app_label}.access_{match.url_name}"

        if not user.has_perm(permission_name):
            raise PermissionDenied(
                "Nie masz uprawnień do tego widoku. Skontaktuj się z właścicielem firmy."
            )


class SubscriptionRequiredMiddleware:
    """
    Jeśli:
    - użytkownik jest zalogowany
    - ma firmę
    - i jego trial wygasł albo nie ma aktywnej subskrypcji

    -> przekieruj na stronę wyboru pakietu.
    """

    # Nazwy URL-i, które NIE są blokowane
    EXEMPT_URL_NAMES = {
        "login",
        "logout",
        "register",
        "forgot",
        'setpassword',
        "employee_ownership_transfer_confirm",
        "select_plan",   # nasza strona wyboru pakietu
        "admin:index",
    }

    # Ścieżki, które omijamy (statyczne pliki itp.)
    EXEMPT_PREFIXES = (
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # logika przed view
        response = self.process_request(request)
        if response:
            return response

        response = self.get_response(request)
        return response

    def process_request(self, request):
        # użytkownik niezalogowany – nic nie blokujemy
        if not request.user.is_authenticated:
            return None

        if not request.user.is_superuser and (
            not request.user.is_active
            or not getattr(request.user, "is_active_employee", True)
        ):
            logout(request)
            return redirect_to_login(
                request.get_full_path(),
                login_url=reverse("login"),
            )

        path = request.path

        # statyczne / media – pomijamy
        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return None

        # sprawdź nazwę url, żeby ominąć np. login / select_plan
        try:
            match = resolve(path)
        except Resolver404:
            return None

        if match.url_name in self.EXEMPT_URL_NAMES:
            return None

        # jeśli użytkownik nie ma firmy – możesz np. puścić dalej
        # albo przekierować gdzieś indziej (np. kreator firmy)
        company = getattr(request.user, "company", None)
        if not company:
            return None

        # znajdź ostatnią subskrypcję firmy
        subscription = company.subscriptions.order_by("-created_at").first()
        request.current_subscription = subscription  # żeby mieć pod ręką w view-ach

        # brak jakiejkolwiek subskrypcji -> blokada
        if not subscription:
            return redirect("select_plan")

        # jeśli pakiet trial i trial wygasł -> blokada
        if subscription.package == Subscription.Package.TRIAL and subscription.is_trial_expired:
            return redirect("select_plan")

        # Anulowana subskrypcja działa do końca opłaconego okresu. Kontrolujemy
        # również datę lokalnie, aby opóźniony webhook Stripe nie przedłużył dostępu.
        if subscription.is_access_expired:
            return redirect("select_plan")

        if subscription.status in [
            Subscription.STATUS_PAST_DUE,
            Subscription.STATUS_UNPAID,
        ]:
            return redirect("select_plan")

        # wszystko ok – wpuszczamy
        return None


class PackageLimitsMiddleware(MiddlewareMixin):
    APP_FEATURES = {
        "dokument": "dokumenty",
        "faktura": "faktury",
        "gwarancja": "gwarancje",
        "kalendarz": "kalendarz",
        "klient": "klienci",
        "magazyn": "magazyn",
        "obsluga": "obsluga",
        "oferta_praca": "oferty",
        "pojazd": "pojazdy",
        "praca": "prace",
        "protokol": "protokoly",
        "rcp": "rcp",
        "serwis": "serwisy",
        "sprzet": "sprzet",
        "urzadzenie": "urzadzenia",
        "zadanie": "zadania",
    }
    RCP_ADVANCED_VIEWS = {
        "time_entry_request_approve",
        "time_entry_request_reject",
        "time_entry_request_list",
    }

    def process_view(self, request, view_func, view_args, view_kwargs):
        return self.check_feature(request)

    def process_exception(self, request, exception):
        if isinstance(exception, SubscriptionLimitExceeded):
            return self.limit_response(request, "; ".join(exception.messages))
        return None

    def check_feature(self, request):
        if not request.user.is_authenticated:
            return None
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return None

        view = getattr(match.func, "view_class", match.func)
        module_parts = getattr(view, "__module__", "").split(".")
        if len(module_parts) < 2 or module_parts[0] != "app":
            return None

        feature = self.APP_FEATURES.get(module_parts[1])
        if module_parts[1] == "core" and match.url_name in {
            "user_calendar", "user_calendar_events"
        }:
            feature = "kalendarz"
        if match.url_name in self.RCP_ADVANCED_VIEWS:
            feature = "rcp_adv"
        if not feature:
            return None

        subscription = getattr(request, "current_subscription", None)
        if subscription is None:
            company = getattr(request.user, "company", None)
            subscription = (
                company.subscriptions.order_by("-created_at").first()
                if company else None
            )
        if subscription and not subscription.has_feature(feature):
            return self.limit_response(
                request,
                "Ten moduł nie jest dostępny w aktualnym pakiecie.",
            )
        return None

    def limit_response(self, request, message):
        if (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        ):
            return JsonResponse({"detail": message}, status=403)
        messages.error(request, message)
        return redirect("select_plan")


class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, "timezone", None):
            timezone.activate(ZoneInfo(request.user.timezone))
        else:
            timezone.deactivate()
        return self.get_response(request)
