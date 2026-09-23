from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.views.generic import DetailView

from app.oferta_praca.models import Offer, OfferVariant, OfferVariantItem, OfferVariantFile, OfferActivity
from app.oferta_praca.services import log_offer_activity

User = get_user_model()


class OfferDetailView(LoginRequiredMixin, DetailView):
    model = Offer
    template_name = "app/oferta_praca/offer_detail.html"
    context_object_name = "offer"

    def get_queryset(self):
        return (
            Offer.objects
            .filter(company=self.request.user.company)
            .select_related("client", "location", "approved_by", "company")
            .prefetch_related(
                "images",
                "assigned_employees",
                "activities",
                Prefetch(
                    "variants",
                    queryset=OfferVariant.objects.prefetch_related(
                        Prefetch(
                            "items",
                            queryset=OfferVariantItem.objects.select_related("product")
                        ),
                        Prefetch(
                            "files",
                            queryset=OfferVariantFile.objects.all()
                        ),
                    ).order_by("id")
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        offer = context["offer"]

        context["workers"] = User.objects.filter(
            company=self.request.user.company,
            is_active=True,
        ).order_by("first_name", "last_name", "email")

        selected_variants = offer.variants.filter(is_selected=True)

        context["selected_variants"] = selected_variants
        context["is_approved"] = selected_variants.exists()
        context["has_selected_variant"] = context["is_approved"]

        context["activities"] = offer.activities.select_related("created_by").order_by("-created_at", "-id")
        context["activities_count"] = offer.activities.count()

        return context