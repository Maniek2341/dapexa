from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from app.urzadzenie.forms import ProductCreateForm
from app.urzadzenie.models import Product, ProductActivity


class ProductUpdateView(LoginRequiredMixin, View):
    template_name = "app/urzadzenie/add.html"

    def get_product(self):
        return get_object_or_404(
            Product,
            pk=self.kwargs["pk"],
            company=self.request.user.company,
        )

    def get(self, request, pk):
        product = self.get_product()
        form = ProductCreateForm(instance=product, user=request.user)

        return render(request, self.template_name, {
            "form": form,
            "product": product,
        })

    def post(self, request, pk):
        product = self.get_product()

        old_net_price = product.net_price
        old_vat_rate = product.vat_rate
        old_is_active = product.is_active

        form = ProductCreateForm(
            request.POST,
            instance=product,
            user=request.user,
        )

        if form.is_valid():
            product = form.save()

            ProductActivity.objects.create(
                company=request.user.company,
                product=product,
                type=ProductActivity.Type.UPDATED,
                title="Edytowano produkt",
                description=f"Zmieniono dane produktu: {product.name}.",
                created_by=request.user,
            )

            if old_net_price != product.net_price or old_vat_rate != product.vat_rate:
                ProductActivity.objects.create(
                    company=request.user.company,
                    product=product,
                    type=ProductActivity.Type.PRICE,
                    title="Zmieniono cenę",
                    description=(
                        f"Cena netto: {old_net_price} zł → {product.net_price} zł. "
                        f"VAT: {old_vat_rate}% → {product.vat_rate}%."
                    ),
                    created_by=request.user,
                )

            if old_is_active != product.is_active:
                ProductActivity.objects.create(
                    company=request.user.company,
                    product=product,
                    type=ProductActivity.Type.STATUS,
                    title="Zmieniono status produktu",
                    description=(
                        "Produkt aktywny."
                        if product.is_active
                        else "Produkt oznaczono jako nieaktywny."
                    ),
                    created_by=request.user,
                )

            messages.success(request, "Produkt został zaktualizowany.")
            return redirect("product_detail", pk=product.pk)

        messages.error(request, "Popraw błędy w formularzu.")

        return render(request, self.template_name, {
            "form": form,
            "product": product,
        })