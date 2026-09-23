from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import DetailView

from app.urzadzenie.models import Product, ProductActivity
from app.magazyn.models import StockItem, StockMovement
from app.oferta_praca.models import OfferVariantItem
from app.protokol.models import ProtokolUrzadzenia
from django.core.exceptions import PermissionDenied
from app.urzadzenie.permissions import can_view_product_detail


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = "app/urzadzenie/detail.html"
    context_object_name = "product"

    def get_queryset(self):
        if not can_view_product_detail(self.request.user):
            raise PermissionDenied
        return (
            Product.objects
            .filter(company=self.request.user.company)
            .select_related("category")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = self.object
        company = self.request.user.company

        net_price = product.net_price or 0
        vat_rate = product.vat_rate or 0
        gross_price = net_price + (net_price * vat_rate / 100)

        # =========================
        # MAGAZYN
        # =========================

        stock_items_qs = (
            StockItem.objects
            .filter(
                company=company,
                product=product,
            )
            .select_related("warehouse")
            .order_by("warehouse__name")
        )

        stock_summary = stock_items_qs.aggregate(
            total_quantity=Sum("quantity"),
            total_min_quantity=Sum("min_quantity"),
        )

        stock_movements_qs = (
            StockMovement.objects
            .filter(
                company=company,
                product=product,
            )
            .select_related("warehouse")
            .order_by("-id")
        )
        product_activities_qs = (
            ProductActivity.objects
            .filter(
                company=company,
                product=product,
            )
            .select_related("created_by")
            .order_by("-created_at", "-id")
        )

        context["product_activities"] = product_activities_qs[:10]
        context["product_activities_count"] = product_activities_qs.count()

        stock_movements_count = stock_movements_qs.count()
        stock_movements = stock_movements_qs[:10]

        # =========================
        # OFERTY
        # =========================

        offer_items_qs = (
            OfferVariantItem.objects
            .filter(
                product=product,
                company=company,
            )
            .select_related(
                "variant",
                "variant__offer",
                "variant__offer__client",
            )
            .order_by("-variant__offer__issue_date", "-id")
        )

        offer_items_count = offer_items_qs.count()
        offer_items = offer_items_qs[:10]

        # =========================
        # PROTOKOŁY
        # =========================

        protocol_items_qs = (
            ProtokolUrzadzenia.objects
            .filter(
                urzadzenia=product,
                protokol__company=company,
            )
            .select_related(
                "protokol",
                "protokol__client",
                "protokol__service",
                "protokol__work_order",
            )
            .order_by("-protokol__created_at")
        )

        protocol_items_count = protocol_items_qs.count()
        protocol_items = protocol_items_qs[:10]

        context.update({
            "gross_price": gross_price,

            "stock_items": stock_items_qs,
            "stock_movements": stock_movements,
            "stock_movements_count": stock_movements_count,
            "total_quantity": stock_summary["total_quantity"] or 0,
            "total_min_quantity": stock_summary["total_min_quantity"] or 0,
            "warehouse_count": stock_items_qs.count(),

            "offer_items": offer_items,
            "offer_items_count": offer_items_count,

            "protocol_items": protocol_items,
            "protocol_items_count": protocol_items_count,
        })

        return context
