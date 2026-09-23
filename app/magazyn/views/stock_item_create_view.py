from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from app.magazyn.forms import StockItemCreateForm
from app.urzadzenie.models import ProductActivity
from django.core.exceptions import PermissionDenied
from app.magazyn.permissions import can_manage_stock


class StockItemCreateView(LoginRequiredMixin, View):
    template_name = "app/magazyn/add.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_stock(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = StockItemCreateForm(user=request.user)

        return render(request, self.template_name, {
            "form": form,
        })

    def post(self, request):
        form = StockItemCreateForm(request.POST, user=request.user)

        if form.is_valid():
            stock_item = form.save(commit=False)
            stock_item.company = request.user.company
            stock_item.save()

            ProductActivity.objects.create(
                company=request.user.company,
                product=stock_item.product,
                type=ProductActivity.Type.STOCK,
                title="Dodano produkt na magazyn",
                description=(
                    f"Produkt dodano do magazynu {stock_item.warehouse.name}. "
                    f"Ilość początkowa: {stock_item.quantity} {stock_item.product.unit}. "
                    f"Minimum: {stock_item.min_quantity} {stock_item.product.unit}."
                ),
                created_by=request.user,
            )

            messages.success(request, "Produkt został dodany na magazyn.")
            return redirect("stock_list")

        messages.error(request, "Popraw błędy w formularzu.")

        return render(request, self.template_name, {
            "form": form,
        })
