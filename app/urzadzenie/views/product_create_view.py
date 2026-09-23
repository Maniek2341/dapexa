from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from app.urzadzenie.forms import ProductCreateForm
from app.urzadzenie.models import ProductActivity
from django.core.exceptions import PermissionDenied
from app.urzadzenie.permissions import can_create_product


class ProductCreateView(LoginRequiredMixin, View):
    template_name = "app/urzadzenie/add.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_create_product(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = ProductCreateForm(user=request.user)

        return render(request, self.template_name, {
            "form": form,
        })

    def post(self, request):
        form = ProductCreateForm(request.POST, user=request.user)

        if form.is_valid():
            product = form.save(commit=False)
            product.company = request.user.company
            product.save()

            ProductActivity.objects.create(
                company=request.user.company,
                product=product,
                type=ProductActivity.Type.CREATED,
                title="Dodano produkt",
                description=f"Utworzono pozycję katalogu: {product.name}",
                created_by=request.user,
            )

            messages.success(request, "Pozycja katalogu została dodana.")
            return redirect("product_detail", pk=product.pk)

        messages.error(request, "Popraw błędy w formularzu.")

        return render(request, self.template_name, {
            "form": form,
            "product": None,
        })
