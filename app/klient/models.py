# app/clients/models.py
from django.conf import settings
from django.db import models

from app.core.models import Address, CompanyOwnedModel
from app.core.view_permissions import view_permissions


class Client(CompanyOwnedModel):
    TYPE_PRIVATE = "private"
    TYPE_COMPANY = "company"

    TYPE_CHOICES = [
        (TYPE_PRIVATE, "Osoba prywatna"),
        (TYPE_COMPANY, "Firma"),
    ]

    client_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_PRIVATE,
    )

    # Dla osoby prywatnej
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    # Dla firmy – nazwa + NIP (ale pole name może też być użyte jako "pełne imię i nazwisko" jeśli chcesz)
    name = models.CharField(max_length=255, blank=True)
    nip = models.CharField(max_length=20, blank=True)

    # Dane kontaktowe (wspólne)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    # Adresy
    billing_address = models.OneToOneField(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_billing",
    )
    shipping_address = models.OneToOneField(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_shipping",
    )

    caretaker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients",
        verbose_name="Opiekun klienta",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Notatki",
        help_text="Wewnętrzne notatki dotyczące klienta",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        # Firma – pokazuj nazwę
        if self.client_type == self.TYPE_COMPANY and self.name:
            return self.name

        # Osoba prywatna – imię + nazwisko
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()

        # Fallback
        if self.name:
            return self.name

        return f"Klient #{self.pk}"

    class Meta:
        verbose_name = 'Klient'
        verbose_name_plural = 'Klienci'
        permissions = view_permissions(
            "klient", "klient_add", "klient_edit", "klient_detail",
            "klient_delete", "klient_deactivate", "klient_archive",
            "klient_activate", "client_note_pin", "client_note_delete",
            "contact_person_add", "location_add", "location_edit",
            "location_delete",
        )


class ContactPerson(CompanyOwnedModel):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="contacts"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.client})"

    class Meta:
        verbose_name = 'Osoba kontaktowa'
        verbose_name_plural = 'Osoby kontaktowe'


class ClientActivity(CompanyOwnedModel):
    class Type(models.TextChoices):
        KLIENT = "client", "Klient"
        NOTE = "note", "Notatka"
        CALL = "call", "Rozmowa"
        EMAIL = "email", "E-mail"
        TASK = "task", "Zadanie"
        SERVICE = "service", "Serwis"
        OFFER = "offer", "Oferta"
        INVOICE = "invoice", "Faktura"
        STATUS = "status", "Zmiana statusu"
        FILE = "file", "Plik"
        OTHER = "other", "Inne"

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    type = models.CharField(max_length=20, choices=Type.choices, default=Type.NOTE)
    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")

    related_app = models.CharField(max_length=50, blank=True, default="")
    related_model = models.CharField(max_length=50, blank=True, default="")
    related_id = models.CharField(max_length=50, blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_client_activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_client_activities")
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["company", "client", "created_at"]),
            models.Index(fields=["company", "type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.client_id} {self.type} {self.title}".strip()


class ClientNote(CompanyOwnedModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="notes_list")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    is_pinned = models.BooleanField(default=False) 

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["company", "client", "created_at"]),
            models.Index(fields=["company", "client", "is_pinned", "created_at"]),
        ]

    def __str__(self):
        return f"Note {self.client_id} {self.created_at:%Y-%m-%d}"

class ClientLocation(CompanyOwnedModel):
    """
    Lokalizacja klienta = obiekt/oddział/miejsce realizacji usług.
    Klient może mieć wiele lokalizacji.
    """
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="locations",
    )

    name = models.CharField(max_length=200, blank=True, default="")  # np. "Magazyn", "Oddział W-wa"
    code = models.CharField(max_length=50, blank=True, default="")   # np. wewnętrzny kod obiektu

    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_locations",
    )

    contact_person = models.ForeignKey(
        ContactPerson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locations",
    )

    notes = models.TextField(blank=True, default="")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Lokalizacja klienta"
        verbose_name_plural = "Lokalizacje klienta"
        ordering = ["-is_default", "name", "id"]
        indexes = [
            models.Index(fields=["company", "client", "is_active"]),
            models.Index(fields=["company", "client", "is_default"]),
        ]
        constraints = [
            # tylko jedna domyślna lokalizacja na klienta (w obrębie firmy)
            models.UniqueConstraint(
                fields=["company", "client"],
                condition=models.Q(is_default=True),
                name="uniq_default_location_per_client_company",
            )
        ]

    def __str__(self):
        label = self.name or "Lokalizacja"
        return f"{label} ({self.client_id})"
