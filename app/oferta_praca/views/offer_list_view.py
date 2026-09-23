from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Prefetch
from django.views.generic import ListView

from app.klient.models import Client
from app.oferta_praca.models import Offer, OfferVariant


class OfferListView(LoginRequiredMixin, ListView):
    model = Offer
    template_name = "app/oferta_praca/offer_list.html"
    context_object_name = "offers"
    paginate_by = 20

    def get_queryset(self):
        company = self.request.user.company
        active_status = self.request.GET.get("status", "nowe")

        qs = (
            Offer.objects
            .filter(company=company)
            .select_related("client", "approved_by", "company", "location")
            .prefetch_related(
                "images",
                Prefetch(
                    "variants",
                    queryset=OfferVariant.objects.only(
                        "id",
                        "offer_id",
                        "is_selected",
                        "total_netto",
                        "total_brutto",
                    )
                )
            )
            .order_by("-issue_date", "-id")
        )

        status_map = {
            "spotkanie": Offer.STATUS_SPOTKANIE,
            "do_zrobienia": Offer.STATUS_DOZROBIENIA,
            "przygotowane": Offer.STATUS_PRZYGOTOWANE,
            "wyslane": Offer.STATUS_WYSLANE,
            "nieaktualne": Offer.STATUS_NIEAKTUALNE,
            "przekazane": Offer.STATUS_PRZEKAZANE,
            "nowe": Offer.STATUS_NOWE,
        }

        if active_status != "all" and active_status in status_map:
            qs = qs.filter(status=status_map[active_status])

        q = self.request.GET.get("q", "").strip()
        priority = self.request.GET.get("priority", "").strip()
        client_id = self.request.GET.get("client", "").strip()

        if q:
            qs = qs.filter(
                models.Q(number__icontains=q) |
                models.Q(title__icontains=q) |
                models.Q(description__icontains=q) |
                models.Q(order_number__icontains=q) |
                models.Q(client__name__icontains=q)
            )

        if priority:
            qs = qs.filter(priority=priority)

        if client_id:
            qs = qs.filter(client_id=client_id)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.request.user.company

        context["active_status"] = self.request.GET.get("status", "nowe")
        context["priority_choices"] = Offer.Priority.choices
        context["clients"] = Client.objects.filter(company=company).order_by("name")

        context["filters"] = {
            "q": self.request.GET.get("q", "").strip(),
            "priority": self.request.GET.get("priority", "").strip(),
            "client": self.request.GET.get("client", "").strip(),
        }
        return context