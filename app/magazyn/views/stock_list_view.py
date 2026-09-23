from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F
from django.views.generic import ListView

from app.magazyn.models import StockItem, Warehouse
from app.magazyn.permissions import can_manage_stock


class StockListView(LoginRequiredMixin, ListView):
    model = StockItem
    template_name = "app/magazyn/stock_list.html"
    context_object_name = "stock_items"
    paginate_by = 30

    def get_queryset(self):
        queryset = (
            StockItem.objects
            .filter(company=self.request.user.company)
            .select_related("warehouse", "product", "product__category")
            .order_by("product__name", "warehouse__name")
        )

        q = self.request.GET.get("q", "").strip()
        warehouse = self.request.GET.get("warehouse", "").strip()
        status = self.request.GET.get("status", "").strip()

        if q:
            queryset = queryset.filter(
                Q(product__name__icontains=q) |
                Q(product__sku__icontains=q)
            )

        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)

        if status == "low":
            queryset = queryset.filter(quantity__lt=F("min_quantity"))

        elif status == "ok":
            queryset = queryset.filter(quantity__gte=F("min_quantity"))

        elif status == "empty":
            queryset = queryset.filter(quantity__lte=0)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["warehouses"] = Warehouse.objects.filter(
            company=self.request.user.company,
        ).order_by("name")

        context["filters"] = {
            "q": self.request.GET.get("q", ""),
            "warehouse": self.request.GET.get("warehouse", ""),
            "status": self.request.GET.get("status", ""),
        }
        context["can_manage_stock"] = can_manage_stock(self.request.user)

        return context
