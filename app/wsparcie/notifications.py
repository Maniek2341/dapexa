import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse

from app.core.emails import build_email_url

logger = logging.getLogger(__name__)

SUPPORT_EMAIL = "kontakt@dapexa.com"


def notify_support_ticket(ticket):
    """Send a support ticket summary to the Dapexa support mailbox."""
    creator = ticket.created_by
    creator_name = creator.get_full_name().strip() if creator else ""
    creator_email = creator.email if creator else "brak"
    ticket_url = build_email_url(
        reverse("support_detail", kwargs={"pk": ticket.pk})
    )
    subject = f"Nowe zgłoszenie wsparcia #{ticket.pk}"
    message = "\n".join([
        f"Temat: {ticket.title}",
        f"Firma: {ticket.company.name}",
        f"Zgłaszający: {creator_name or creator_email} ({creator_email})",
        f"Moduł: {ticket.module or 'Nie podano'}",
        f"Priorytet: {ticket.get_priority_display()}",
        "",
        "Opis zgłoszenia:",
        ticket.description,
        "",
        f"Otwórz zgłoszenie: {ticket_url}",
    ])

    def deliver():
        try:
            sent = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[SUPPORT_EMAIL],
                fail_silently=False,
            )
            if sent != 1:
                logger.error("Backend pocztowy nie przyjął powiadomienia o zgłoszeniu #%s", ticket.pk)
        except Exception:
            # Błąd poczty nie powinien usuwać zgłoszenia ani przerywać obsługi formularza.
            logger.exception("Nie udało się powiadomić wsparcia o zgłoszeniu #%s", ticket.pk)

    transaction.on_commit(deliver)
