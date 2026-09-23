from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.db import transaction

from app.magazyn.forms import StockMovementForm
from app.magazyn.models import StockItem, StockMovement
from app.urzadzenie.models import ProductActivity
from django.core.exceptions import PermissionDenied
from app.magazyn.permissions import can_manage_stock


class StockInView(LoginRequiredMixin, View):
    def get_stock(self):
        return get_object_or_404(
            StockItem,
            pk=self.kwargs["pk"],
            company=self.request.user.company,
        )

    @transaction.atomic
    def post(self, request, pk):
        if not can_manage_stock(request.user):
            raise PermissionDenied
        stock = self.get_stock()
        form = StockMovementForm(request.POST)

        if form.is_valid():
            quantity = form.cleaned_data["quantity"]
            document_number = form.cleaned_data.get("document_number", "")
            note = form.cleaned_data.get("note", "")

            StockMovement.objects.create(
                company=request.user.company,
                warehouse=stock.warehouse,
                product=stock.product,
                type=StockMovement.MovementType.IN,
                quantity=quantity,
                document_number=document_number,
                note=note,
            )

            stock.quantity += quantity
            stock.save(update_fields=["quantity"])

            ProductActivity.objects.create(
                company=request.user.company,
                product=stock.product,
                type=ProductActivity.Type.STOCK,
                title="Przyjęcie na magazyn",
                description=(
                    f"Przyjęto {quantity} {stock.product.unit} "
                    f"do magazynu {stock.warehouse.name}."
                    + (f" Dokument: {document_number}." if document_number else "")
                ),
                created_by=request.user,
            )

            messages.success(request, "Przyjęto produkt na magazyn.")
            return redirect("stock_list")

        messages.error(request, "Nie udało się przyjąć produktu na magazyn.")
        return redirect("stock_list")
