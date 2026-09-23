# app/protocols/models.py
from decimal import Decimal
import os
from django.conf import settings
from django.db import models
from django.dispatch import receiver
from app.core.routing import RoutingService
from app.urzadzenie.models import Product
from app.serwis.models import ServiceOrder
from app.core.models import Address, CompanyOwnedModel, CompanySettings, PanelUser
from app.core.fields import TrackedFileField, TrackedImageField, file_size_field
from app.core.view_permissions import view_permissions
from app.klient.models import Client, ClientLocation
from django.core.exceptions import ValidationError
from django.utils import timezone
from app.dokument.models import DocumentFolder


def user_directory_path(instance, filename):
    return (
        f"companies/{instance.protokol.company_id}/"
        f"protocols/{instance.protokol.id}/"
        f"images/{filename}"
    )

class Protocol(CompanyOwnedModel):
    class Status(models.TextChoices):
        NEW = "new", "Nowe"
        OBSLUGA = "obsluga", "Obsługa"
        GWARANCJA = "gwarancja", "Gwarancja"
        DO_ZAFAKTUROWANIA = "do_zafakturowania", "Do zafakturowania"
        SENT = "sent", "Wysłane i zafakturowane"

    class VAT(models.TextChoices):
        VAT_8 = "vat_8", "8"
        VAT_23 = "vat_23", "23"

    class Wysylka(models.TextChoices):
        MAIL = "mail", "Mailowo"
        LIST = "list", "Listownie"

    class RodzajPrac(models.TextChoices):
        NAPRAWA = "naprawa", "Naprawa"
        ROZBUDOWA = "rozbudowa", "Rozbudowa"
        MONTAZ = "montaz", "Montaż"
        PRZEGLAD = "przeglad", "Przegląd"
        ZGRANIE = "zgranie", "Obsługa"
        PRACA = "praca", "Praca"
        DOSTAWA = "dostawa", "Dostawa"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )
    end_time = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=50)
    service = models.OneToOneField(ServiceOrder, on_delete=models.CASCADE, related_name="protocol", blank=True, null=True)
    work_order = models.OneToOneField(
        "praca.WorkOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="protocol",
    )
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="protocols")
    wykonane_prace = models.TextField(max_length=250, blank=True, null=True)
    opis = models.TextField(max_length=250, blank=True, null=True)
    dodatkowe_materialy = models.TextField(max_length=250, blank=True, null=True)
    robocizna = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    rodzaj_prac = models.CharField(choices=RodzajPrac.choices, default=RodzajPrac.NAPRAWA, max_length=20,)
    signed_by_client = models.BooleanField(default=False)
    signed_by_employee = models.BooleanField(default=False)
    pracownik = models.ForeignKey(PanelUser, related_name="userprot", on_delete=models.SET_NULL, blank=True, null=True)
    pracownicy_szt = models.IntegerField(blank=True, null=True, default=1)
    dojazdy_szt = models.IntegerField(default=1, blank=True, null=True)
    ile_vat = models.CharField(choices=VAT.choices, blank=True, null=True)
    protokol_ceny = models.BooleanField(blank=True, null=True)
    protokol_bez_ceny = models.BooleanField(blank=True, null=True)
    czy_powykonawcza = models.BooleanField(blank=True, null=True)
    sposob_wysylki = models.CharField(choices=Wysylka.choices, blank=True, null=True)
    dodatkowe_info_pracownik = models.TextField(max_length=250, blank=True, default="")
    dodatkowy_komentarz = models.TextField(max_length=250, blank=True, null=True)
    is_praca = models.BooleanField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    protocol_description = models.TextField(blank=True)

    client_signature = TrackedImageField(
        upload_to="protocols/signatures/",
        blank=True,
        null=True
    )
    client_signature_size = file_size_field("Rozmiar podpisu klienta")

    employee_signature = TrackedImageField(
        upload_to="protocols/signatures/",
        blank=True,
        null=True
    )
    employee_signature_size = file_size_field("Rozmiar podpisu pracownika")

    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocols",
    )

    address_street = models.CharField(max_length=255, blank=True)
    address_city = models.CharField(max_length=100, blank=True)
    address_postal_code = models.CharField(max_length=20, blank=True)
    address_country = models.CharField(max_length=100, blank=True)
    address_latitude = models.FloatField(null=True, blank=True)
    address_longitude = models.FloatField(null=True, blank=True)

    location = models.ForeignKey(
        ClientLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocols",
        verbose_name="Lokalizacja"
    )

    materials_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # ----------------------------------
    # 🚗 DOJAZD
    # ----------------------------------

    distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Ilość km"
    )

    travel_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Koszt dojazdu"
    )

    # ----------------------------------
    # 👷 ROBOCIZNA
    # ----------------------------------

    labor_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Koszt robocizny"
    )

    # ----------------------------------
    # 🧾 PODSUMOWANIE
    # ----------------------------------

    net_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Suma netto"
    )

    def __str__(self):
        return self.number

    @classmethod
    def generate_number(cls, company, year):
        company_settings = CompanySettings.objects.filter(company=company).first()
        prefix = company_settings.protocol_number_prefix if company_settings else "PROT"
        digits = company_settings.protocol_number_digits if company_settings else 5
        number_prefix = f"{prefix}/{year}/"
        sequences = []
        for number in cls.objects.filter(
            company=company,
            number__startswith=number_prefix,
        ).values_list("number", flat=True):
            try:
                sequences.append(int(number.rsplit("/", 1)[-1]))
            except (AttributeError, TypeError, ValueError):
                continue
        sequence = max(sequences, default=0) + 1
        return f"{number_prefix}{sequence:0{digits}d}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "number"],
                name="unique_protocol_number_per_company"
            )
        ]
        verbose_name = 'Protokol'
        verbose_name_plural = 'Protokoly'
        permissions = view_permissions(
            "protokol_nowe", "protokol_add", "protokol_detail",
            "protocol_change_status", "protocol_media_delete", "protocol_delete",
            "protocol_edit", "protocol_from_service", "protocol_pdf",
            "protocol_from_work",
        )
    
    def save(self, *args, **kwargs):
        if not self.end_time:
            self.end_time = timezone.now()

        if not self.number:
            year = self.end_time.year
            self.number = self.generate_number(self.company, year)

        super().save(*args, **kwargs)
    
    def clean(self):
        if self.pk:
            old = Protocol.objects.filter(pk=self.pk).first()
            if old and old.signed_by_client:
                raise ValidationError("Nie można edytować podpisanego protokołu.")
    
    def recalculate(self, user):
        """
        Przelicza:
        - dystans
        - koszt dojazdu
        - koszt robocizny
        - koszt materiałów
        - pełne netto
        """

        distance_one_way = Decimal("0.00")
        total_km = Decimal("0.00")

        # ==============================
        # 🚗 DYSTANS
        # ==============================

        try:
            company_address = user.company.main_address

            if self.location and self.location.address:
                client_address = self.location.address
            elif self.client and self.client.shipping_address:
                client_address = self.client.shipping_address
            else:
                client_address = None

            if (
                company_address
                and client_address
                and company_address.latitude
                and company_address.longitude
                and client_address.latitude
                and client_address.longitude
            ):
                raw_distance = RoutingService.get_distance(
                    company_address,
                    client_address
                )

                if raw_distance:
                    distance_one_way = Decimal(str(raw_distance))

        except Exception as e:
            print("DISTANCE ERROR:", e)

        dojazdy = Decimal(str(self.dojazdy_szt or 1))

        total_km = (
            distance_one_way
            * Decimal("2")
            * dojazdy
        ).quantize(Decimal("0.01"))

        self.distance_km = total_km

        # ==============================
        # 💰 DOJAZD
        # ==============================

        settings = CompanySettings.objects.filter(
            company=user.company
        ).first()

        if settings:
            self.travel_price_per_km = settings.travel_cost_per_km
            self.travel_cost = (
                total_km * settings.travel_cost_per_km
            ).quantize(Decimal("0.01"))
        else:
            self.travel_price_per_km = Decimal("0.00")
            self.travel_cost = Decimal("0.00")

        # ==============================
        # 👷 ROBOCIZNA
        # ==============================

        labor_cost = Decimal("0.00")
        pracownicy = self.pracownicy_szt or 1
        hours = Decimal(str(self.robocizna or 0))

        if settings:

            if pracownicy == 1:
                hourly_rate = settings.labor_price_1_worker
            elif pracownicy == 2:
                hourly_rate = settings.labor_price_2_workers
            else:
                hourly_rate = settings.labor_price_3_workers

            labor_cost = (hours * hourly_rate).quantize(Decimal("0.01"))

        self.labor_cost = labor_cost

        # ==============================
        # 📦 MATERIAŁY
        # ==============================

        materials_cost = Decimal("0.00")

        for item in self.protokolurz.all():
            quantity = Decimal(str(item.sztuki or 0))
            unit_price = Decimal(str(item.urzadzenia.net_price or 0))
            materials_cost += quantity * unit_price

        self.materials_cost = materials_cost.quantize(Decimal("0.01"))

        # ==============================
        # 🧮 SUMA NETTO
        # ==============================

        self.net_total = (
            self.travel_cost
            + self.labor_cost
            + self.materials_cost
        ).quantize(Decimal("0.01"))


class ProtokolUrzadzenia(models.Model):
    protokol = models.ForeignKey(Protocol, on_delete=models.CASCADE, related_name="protokolurz")
    urzadzenia = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="urz")
    sztuki = models.IntegerField(blank=True, null=True)
    cenarazem = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)


class ProtokolImage(models.Model):
    class Kind(models.TextChoices):
        IMAGE = "image", "Zdjęcie"
        FILE = "file", "Załącznik"

    protokol = models.ForeignKey(Protocol, on_delete=models.CASCADE, related_name="protokolimg")
    file = TrackedFileField(upload_to=user_directory_path, null=True, blank=True)
    file_size = file_size_field()
    kind = models.CharField(max_length=10, choices=Kind.choices, null=True, blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=255, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="protokol_media_added"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocol_media",
        related_query_name="protocol_medium",
        verbose_name="Folder",
    )

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = getattr(self.file, "name", "") or ""
        if self.protokol_id and not self.folder_id:
            folder, _ = DocumentFolder.objects.get_or_create(
                company=self.protokol.company,
                name="Protokoły",
                parent=None,
            )
            self.folder = folder

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.protokol_id} / {self.kind} / {self.original_name or self.file.name}"

@receiver(models.signals.post_delete, sender=ProtokolImage)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.file and instance.file.path:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)



class ProtocolActivity(CompanyOwnedModel):
    class Type(models.TextChoices):
        SYSTEM = "system", "System"
        NOTE = "note", "Notatka"
        STATUS = "status", "Zmiana statusu"
        SIGNATURE = "signature", "Podpis"
        FILE = "file", "Plik"
        OTHER = "other", "Inne"

    protocol = models.ForeignKey(
        "Protocol",
        on_delete=models.CASCADE,
        related_name="activities"
    )

    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM
    )

    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_protocol_activities",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "protocol", "created_at"]),
            models.Index(fields=["company", "type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.protocol_id} {self.type} {self.title}".strip()
