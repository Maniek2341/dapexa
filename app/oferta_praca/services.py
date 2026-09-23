from app.oferta_praca.models import OfferActivity


def log_offer_activity(offer, user=None, type=OfferActivity.Type.SYSTEM, title="", description=""):
    return OfferActivity.objects.create(
        company=offer.company,
        offer=offer,
        type=type,
        title=title,
        description=description or "",
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )