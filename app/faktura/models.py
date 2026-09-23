# app/invoices/models.py
from django.db import models
from app.core.models import CompanyOwnedModel
from app.klient.models import Client
from app.protokol.models import Protocol
from app.oferta_praca.models import Offer


class VatExemptionReason(models.Model):
    code = models.CharField(max_length=50, unique=True)  # np. "ZW", "np."
    description = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.description}"


class Invoice(CompanyOwnedModel):
    class VatMode(models.TextChoices):
        STANDARD = "standard", "Standardowy VAT"
        EXEMPT = "exempt", "Zwolnienie z VAT"

    class SendingMethod(models.TextChoices):
        EMAIL = "email", "E-mail"
        POST = "post", "Poczta"
        PORTAL = "portal", "Portal klienta"

    number = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="invoices")
    issue_date = models.DateField()
    sale_date = models.DateField()
    due_date = models.DateField()
    payment_method = models.CharField(max_length=50, default="przelew")
    vat_mode = models.CharField(max_length=20, choices=VatMode.choices, default=VatMode.STANDARD)
    vat_exemption_reason = models.ForeignKey(
        VatExemptionReason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sending_method = models.CharField(
        max_length=20,
        choices=SendingMethod.choices,
        default=SendingMethod.EMAIL
    )
    is_final_invoice = models.BooleanField(default=True)
    attach_protocol = models.BooleanField(default=True)
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices"
    )
    offer = models.ForeignKey(
        Offer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices"
    )
    ksef_number = models.CharField(max_length=255, blank=True)
    ksef_status = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = 'Faktura'
        verbose_name_plural = 'Faktury'


class InvoiceItem(CompanyOwnedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    pkwiu = models.CharField(max_length=50, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, default="szt.")
    net_price = models.DecimalField(max_digits=12, decimal_places=2)
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=23)
    is_vat_exempt = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.invoice} - {self.name}"

    class Meta:
        verbose_name = 'Przedmiot faktury'
        verbose_name_plural = 'Przedmioty faktur'