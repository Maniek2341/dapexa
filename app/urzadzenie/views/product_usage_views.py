from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from app.urzadzenie.models import Product
from app.oferta_praca.models import OfferVariantItem
from app.protokol.models import ProtokolUrzadzenia
from app.magazyn.models import StockMovement


class ProductContextMixin(LoginRequiredMixin):
    product = None

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(
            Product,
            pk=kwargs["pk"],
            company=request.user.company,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.product
        return context


class ProductOfferUsageView(ProductContextMixin, ListView):
    template_name = "app/urzadzenie/usage_offers.html"
    context_object_name = "items"
    paginate_by = 25

    def get_queryset(self):
        return (
            OfferVariantItem.objects
            .filter(
                product=self.product,
                company=self.request.user.company,
            )
            .select_related(
                "variant",
                "variant__offer",
                "variant__offer__client",
            )
            .order_by("-variant__offer__issue_date", "-id")
        )


class ProductProtocolUsageView(ProductContextMixin, ListView):
    template_name = "app/urzadzenie/usage_protocols.html"
    context_object_name = "items"
    paginate_by = 25

    def get_queryset(self):
        return (
            ProtokolUrzadzenia.objects
            .filter(
                urzadzenia=self.product,
                protokol__company=self.request.user.company,
            )
            .select_related(
                "protokol",
                "protokol__client",
                "protokol__service",
                "protokol__work_order",
            )
            .order_by("-protokol__created_at", "-id")
        )


class ProductStockHistoryView(ProductContextMixin, ListView):
    template_name = "app/urzadzenie/usage_stock.html"
    context_object_name = "items"
    paginate_by = 25

    def get_queryset(self):
        return (
            StockMovement.objects
            .filter(
                product=self.product,
                company=self.request.user.company,
            )
            .select_related("warehouse")
            .order_by("-id")
        )