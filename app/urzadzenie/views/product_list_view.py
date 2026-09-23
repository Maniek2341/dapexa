from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from app.urzadzenie.models import Product
from app.urzadzenie.permissions import can_create_product, can_view_product_detail


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "app/urzadzenie/list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            Product.objects
            .filter(company=self.request.user.company)
            .select_related("category")
            .order_by("-id")
        )

        q = self.request.GET.get("q")
        product_type = self.request.GET.get("type")
        active = self.request.GET.get("active")

        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(sku__icontains=q)
            )

        if product_type:
            queryset = queryset.filter(type=product_type)

        if active == "1":
            queryset = queryset.filter(is_active=True)

        elif active == "0":
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["product_types"] = Product.ProductType.choices
        context["filters"] = {
            "q": self.request.GET.get("q", ""),
            "type": self.request.GET.get("type", ""),
            "active": self.request.GET.get("active", ""),
        }
        context["can_create_product"] = can_create_product(self.request.user)
        context["can_view_product_detail"] = can_view_product_detail(self.request.user)

        return context
