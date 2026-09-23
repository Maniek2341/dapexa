from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views import View

from app.magazyn.forms import WarehouseCreateForm
from app.magazyn.models import Warehouse
from app.magazyn.permissions import can_manage_stock


class WarehouseCreateView(LoginRequiredMixin, View):
    template_name = "app/magazyn/warehouse_add.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_stock(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {"form": WarehouseCreateForm()})

    def post(self, request):
        form = WarehouseCreateForm(request.POST)
        if form.is_valid():
            warehouse = form.save(commit=False)
            warehouse.company = request.user.company
            if warehouse.is_default:
                Warehouse.objects.filter(company=request.user.company, is_default=True).update(is_default=False)
            warehouse.save()
            messages.success(request, "Magazyn został dodany.")
            return redirect("stock_list")
        return render(request, self.template_name, {"form": form})
