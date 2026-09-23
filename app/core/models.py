# app/core/models.py
from datetime import time
from decimal import Decimal
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.forms import ValidationError

from app.core.geocoding import GeocodingService
from app.core.fields import TrackedFileField, file_size_field
from app.core.notification_preferences import default_notification_modules
from app.core.view_permissions import view_permissions

from .managers import CustomUserManager

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return "Avatary/{0}/{1}".format(instance.email, filename)


def company_logo_directory_path(instance, filename):
    return "Firmy/{0}/logo/{1}".format(instance.pk or "nowa", filename)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CompanyOwnedModel(TimeStampedModel):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="%(class)ss"
    )

    class Meta:
        abstract = True


class Address(models.Model):
    street = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    street_no = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, default="Polska")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = 'Adres'
        verbose_name_plural = 'Adresy'

    def __str__(self):
        return f"{self.street}, {self.postcode} {self.city}"

    
    def _full_address_str(self) -> str:
        parts = [
            (self.street or "").strip(),
            f"{(self.postcode or '').strip()} {(self.city or '').strip()}".strip(),
            (self.country or "").strip(),
        ]
        # usuń puste elementy
        return ", ".join([p for p in parts if p])


    
    def save(self, *args, **kwargs):

        should_geocode = False

        if self.pk:
            # 🔎 pobierz poprzednią wersję z bazy
            old = Address.objects.filter(pk=self.pk).first()

            if old:
                if (
                    old.street != self.street
                    or old.city != self.city
                    or old.postcode != self.postcode
                ):
                    should_geocode = True
        else:
            # 🔥 nowy adres
            should_geocode = True

        if should_geocode:

            lat, lng = GeocodingService.get_coordinates(
                street=self.street,
                city=self.city,
                postcode=self.postcode
            )

            if lat is None or lng is None:
                raise ValidationError(
                    "Nie można znaleźć podanego adresu. Sprawdź dane."
                )

            self.latitude = lat
            self.longitude = lng

        super().save(*args, **kwargs)

# app/core/models.py (lub osobny plik settings_models.py)

class Company(TimeStampedModel):
    name = models.CharField(max_length=255)
    nip = models.CharField(max_length=20, blank=True)
    regon = models.CharField(max_length=20, blank=True)
    krs = models.CharField(max_length=20, blank=True)
    logo = TrackedFileField(
        blank=True,
        null=True,
        upload_to=company_logo_directory_path,
        max_length=500,
        verbose_name="Logo firmy",
    )
    logo_size = file_size_field("Rozmiar loga firmy")
    main_address = models.OneToOneField(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_main"
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Firma'
        verbose_name_plural = 'Firmy'

    def __str__(self):
        return self.name

class CompanySettings(TimeStampedModel):
    company = models.OneToOneField(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="settings",
        null=True,
        blank=True,
    )
    # 🚗 DOJAZD
    travel_cost_per_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Koszt dojazdu za 1 km"
    )

    # 👷 ROBOCIZNA
    labor_price_1_worker = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Cena za 1 pracownika"
    )

    labor_price_2_workers = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Cena za 2 pracowników"
    )

    labor_price_3_workers = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Cena za 3 pracowników"
    )

    # ⏱ STAWKA GODZINOWA
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # 📄 VAT DOMYŚLNY
    default_vat = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=23
    )

    # 🔧 inne ustawienia przyszłościowe
    default_protocol_valid_days = models.IntegerField(default=14)

    # 🕒 DOMYŚLNE GODZINY RCP
    default_work_start_time = models.TimeField(
        default=time(7, 0),
        verbose_name="Domyślna godzina rozpoczęcia pracy",
    )
    default_work_end_time = models.TimeField(
        default=time(15, 0),
        verbose_name="Domyślna godzina zakończenia pracy",
    )

    # 🔢 NUMERACJA
    protocol_number_prefix = models.CharField(
        max_length=12,
        default="PROT",
        verbose_name="Prefiks numeru protokołu",
    )
    protocol_number_digits = models.PositiveSmallIntegerField(
        default=5,
        verbose_name="Liczba cyfr numeru protokołu",
    )
    service_number_prefix = models.CharField(
        max_length=12,
        default="SER",
        verbose_name="Prefiks numeru serwisu",
    )
    maintenance_number_prefix = models.CharField(
        max_length=12,
        default="OBS",
        verbose_name="Prefiks numeru obsługi",
    )
    service_number_digits = models.PositiveSmallIntegerField(
        default=4,
        verbose_name="Liczba cyfr numeru zgłoszenia",
    )

    notification_email = models.EmailField(
        blank=True,
        verbose_name="Firmowy adres powiadomień",
    )
    notification_modules = models.JSONField(
        default=default_notification_modules,
        blank=True,
        verbose_name="Moduły wysyłające powiadomienia firmowe",
    )

    def __str__(self):
        return f"Ustawienia firmy {self.company.name}"

class PanelUser(AbstractUser, TimeStampedModel):
    username = None
    first_name = models.CharField('first name', max_length=150, blank=True)
    last_name = models.CharField('last name', max_length=150, blank=True)

    is_staff = models.BooleanField(
        'staff status',
        default=True,
        help_text='Designates whether the user can log into this admin site.',
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text=
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ,
    )

    is_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    email = models.EmailField('email address', unique=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    GENDER_MALE = 1
    GENDER_FEMALE = 2
    GENDER_CHOICES = [
        (GENDER_MALE, "Mężczyzna"),
        (GENDER_FEMALE, "Kobieta"),
    ]

    avatar = TrackedFileField(blank=True, null=True, upload_to=user_directory_path, max_length=500)
    avatar_size = file_size_field("Rozmiar avatara")

    birthday = models.DateField(blank=True, null=True)
    gender = models.PositiveSmallIntegerField(choices=GENDER_CHOICES, blank=True, default=GENDER_MALE)
    prawko = models.CharField(max_length=250, blank=True, null=True)
    wyksztalcenie = models.CharField(max_length=100, blank=True, null=True)
    badania_lekarskie = models.CharField(max_length=250, blank=True, null=True)
    badania_lekarskie_do = models.DateField(blank=True, null=True)
    phone_priv = models.CharField(max_length=30, blank=True)
    email_notification_modules = models.JSONField(
        default=default_notification_modules,
        blank=True,
        verbose_name="Powiadomienia e-mail z modułów",
    )
    two_factor_enabled = models.BooleanField(
        default=True,
        verbose_name="Weryfikacja dwuetapowa",
    )
    login_2fa_code_hash = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Hash kodu 2FA logowania",
    )
    login_2fa_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ważność kodu 2FA logowania",
    )
    login_2fa_attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Liczba prób kodu 2FA logowania",
    )

    class Role(models.TextChoices):
        OWNER = "owner", "Właściciel"
        MANAGER = "manager", "Manager"
        BIURO = "biuro", "Biuro"
        PODWYKONAWCA = "podwykonawca", "Podwykonawca"
        EMPLOYEE = "employee", "Pracownik"
        CLIENT = "client", "Klient"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )

    phone = models.CharField(max_length=30, blank=True)
    position = models.CharField(max_length=100, blank=True)
    is_active_employee = models.BooleanField(default=True)

    employment_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data zatrudnienia"
    )

    previous_employment_years = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0,
        verbose_name="Staż z poprzednich miejsc pracy (lata)"
    )

    employment_fraction = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.00,
        verbose_name="Wymiar etatu (np. 1.00, 0.50)"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Użytkownik'
        verbose_name_plural = 'Użytkownicy'
        permissions = [
            (
                "delete_company_employee",
                "Może usuwać pracowników swojej firmy",
            ),
        ] + view_permissions(
            "dashboard", "create_checkout_session", "checkout_success",
            "checkout_cancel", "stripe_webhook", "select_plan",
            "purchase_extra_users",
            "change_package",
            "cancel_subscription",
            "user_calendar", "user_calendar_events", "ajax_products",
            "ajax_clients", "ajax_services", "login", "register", "logout",
            "forgot", "setpassword", "resetpassword", "profile",
            "company_settings",
            "user_activate", "employee_add", "employee_edit",
            "employee_delete", "employee_status_toggle", "employee_list", "employee_permission_list",
            "employee_permission_edit", "employee_group_create",
            "employee_group_edit", "employee_group_delete",
            "employee_set_password", "employee_ownership_transfer",
            "employee_ownership_transfer_confirm",
        )
    

    def __str__(self):
        return f"{self.email} ({self.company})"

    def get_total_seniority_years(self):
        if not self.employment_start_date:
            return Decimal(self.previous_employment_years or 0)

        today = timezone.now().date()
        current_years = (today - self.employment_start_date).days / 365
        return Decimal(current_years) + Decimal(self.previous_employment_years or 0)


    def get_vacation_entitlement(self):
        """
        Zwraca limit urlopu wypoczynkowego na dany rok
        uwzględnia staż i wymiar etatu.
        """
        base = Decimal("26") if self.get_total_seniority_years() >= 10 else Decimal("20")
        return (base * Decimal(self.employment_fraction)).quantize(Decimal("0.01"))

class Subscription(models.Model):
    BILLING_MONTHLY = "monthly"
    BILLING_YEARLY = "yearly"
    BILLING_CHOICES = [
        (BILLING_MONTHLY, "Miesięcznie"),
        (BILLING_YEARLY, "Rocznie"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_CANCELED = "canceled"
    STATUS_PAST_DUE = "past_due"
    STATUS_TRIALING = "trialing"
    STATUS_UNPAID = "unpaid"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Aktywna"),
        (STATUS_INCOMPLETE, "Nieukończona"),
        (STATUS_CANCELED, "Anulowana"),
        (STATUS_PAST_DUE, "Zaległa"),
        (STATUS_TRIALING, "Trial"),
        (STATUS_UNPAID, "Nieopłacona"),
    ]

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        null=True,
        blank=True,
    )

    owner = models.ForeignKey(
        "core.PanelUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )

    stripe_customer_id = models.CharField(max_length=255, blank=True)
    # ⬇ WAŻNE: blank=True, null=True – żeby trial nie wymagał id z Stripe
    stripe_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )
    stripe_price_id = models.CharField(max_length=255, blank=True)
    stripe_extra_user_item_id = models.CharField(max_length=255, blank=True)
    extra_users = models.PositiveIntegerField(
        default=0,
        verbose_name="Dokupieni użytkownicy",
    )

    class Package(models.TextChoices):
        TRIAL = "trial", "Trial"
        START = "start", "Start"
        STANDARD = "standard", "Standard"
        PRO = "pro", "Pro"

    # UWAGA: przy rejestracji zawsze TRIAL
    package = models.CharField(
        max_length=20,
        choices=Package.choices,
        default=Package.TRIAL,
        help_text="Pakiet: trial / start / standard / pro",
    )

    # UWAGA: przy rejestracji brak okresu rozliczenia
    billing_period = models.CharField(
        max_length=20,
        choices=BILLING_CHOICES,
        blank=True,
        null=True,
        help_text="Okres rozliczenia (ustawiany dopiero przy płatnym pakiecie).",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INCOMPLETE,
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancellation_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    data_retention_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

     # ---- LIMITY DLA PAKIETÓW (po trialu) ----
    PACKAGE_LIMITS = {
        Package.START: {
            "max_users": 3,
            "max_clients": 50,
            "max_protocols": 70,
            "max_storage_gb": 5,
            "features": {
                "faktury": False,
                "magazyn": False,
                "urzadzenia": True,
                "gwarancje": False,
                "protokoly": True,
                "serwisy": True,
                "klienci": True,
                "zadania": True,
                "pojazdy": True,
                "obsluga": False,
                "sprzet": True,
                "dokumenty": True,
                "prace": False,
                "oferty": False,
                "rcp": True,
                "kalendarz": False,
                "rcp_adv": False,
            },
        },

        Package.STANDARD: {
            "max_users": 10,
            "max_clients": 200,
            "max_protocols": 200,
            "max_storage_gb": 25,
            "features": {
                "faktury": True,
                "magazyn": False,
                "urzadzenia": True,
                "gwarancje": True,
                "protokoly": True,
                "serwisy": True,
                "klienci": True,
                "zadania": True,
                "pojazdy": True,
                "obsluga": True,
                "sprzet": True,
                "dokumenty": True,
                "prace": False,
                "oferty": False,
                "rcp": True,
                "kalendarz": True,
                "rcp_adv": False,
            },
        },

        Package.PRO: {
            "max_users": None,
            "max_clients": None,
            "max_protocols": None,
            "max_storage_gb": 100,
            "features": {
                "faktury": True,
                "magazyn": True,
                "urzadzenia": True,
                "gwarancje": True,
                "protokoly": True,
                "serwisy": True,
                "klienci": True,
                "zadania": True,
                "pojazdy": True,
                "obsluga": True,
                "sprzet": True,
                "dokumenty": True,
                "prace": True,
                "oferty": True,
                "rcp": True,
                "kalendarz": True,
                "rcp_adv": True,
                "client_app": True,
            },
        },
    }

    # ---- LIMITY NA CZAS TRIALA (niezależne od przyszłego pakietu) ----
    TRIAL_LIMITS = {
        "max_users": 1,
        "max_clients": 10,
        "max_protocols": 10,
        "max_storage_gb": 1,
    }


    # ---- HELPERY NA TRIAL ----
    @property
    def is_trial(self) -> bool:
        return self.status == self.STATUS_TRIALING or self.package == self.Package.TRIAL

    @property
    def trial_days_left(self) -> int:
        from django.utils import timezone
        if not self.is_trial or not self.current_period_end:
            return 0
        return (self.current_period_end - timezone.now()).days

    @property
    def is_trial_expired(self) -> bool:
        from django.utils import timezone
        return self.is_trial and self.current_period_end and self.current_period_end < timezone.now()

    @property
    def is_access_expired(self) -> bool:
        """Canceled subscriptions remain usable through the paid period."""
        if self.cancel_at_period_end and self.current_period_end:
            return self.current_period_end <= timezone.now()
        return self.status == self.STATUS_CANCELED

    # ---- AKTUALNE LIMITY (zależne od tego, czy trial czy płatny) ----
    @property
    def limits(self) -> dict:
        """
        Zwraca limity w aktualnym stanie:
        - jeśli pakiet trial -> TRIAL_LIMITS
        - jeśli płatny plan -> PACKAGE_LIMITS dla wybranego pakietu
        """
        if self.package == self.Package.TRIAL:
            return self.TRIAL_LIMITS
        return self.PACKAGE_LIMITS.get(self.package, {})

    @property
    def max_users(self):
        base_limit = self.base_max_users
        if base_limit is None:
            return None
        return base_limit + self.extra_users

    @property
    def base_max_users(self):
        return self.limits.get("max_users")

    @property
    def max_clients(self):
        return self.limits.get("max_clients")

    @property
    def max_protocols(self):
        return self.limits.get("max_protocols")

    @property
    def max_projects(self):
        return self.max_protocols

    @property
    def max_storage_gb(self):
        return self.limits.get("max_storage_gb")

    @property
    def max_storage_bytes(self):
        if self.max_storage_gb is None:
            return None
        return self.max_storage_gb * (1024 ** 3)

    @property
    def storage_used_bytes(self):
        from app.core.subscription_limits import get_company_storage_used_bytes

        return get_company_storage_used_bytes(self.company_id)

    @property
    def storage_used_gb(self):
        return self.storage_used_bytes / (1024 ** 3)

    def has_feature(self, feature):
        if self.package == self.Package.TRIAL:
            return True
        return self.limits.get("features", {}).get(feature, False)

    def __str__(self):
        return f"{self.company} - {self.package} ({self.billing_period or 'brak okresu'})"

class RouteDistanceCache(models.Model):
    origin_lat = models.FloatField()
    origin_lng = models.FloatField()
    dest_lat = models.FloatField()
    dest_lng = models.FloatField()

    distance_km = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "origin_lat",
            "origin_lng",
            "dest_lat",
            "dest_lng",
        )
