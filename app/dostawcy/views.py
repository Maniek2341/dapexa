from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from app.core.models import PanelUser
from app.urzadzenie.models import Product

from .forms import SupplierIntegrationForm
from .models import Supplier, SupplierCompanyProduct, SupplierIntegration, SupplierProduct
from .tasks import sync_supplier_integration


MANAGER_ROLES = {PanelUser.Role.OWNER, PanelUser.Role.MANAGER, PanelUser.Role.BIURO}


def _company(user):
    if not user.company_id:
        raise PermissionDenied
    return user.company


def _require_manager(user):
    if user.role not in MANAGER_ROLES:
        raise PermissionDenied


@login_required
def integration_list(request):
    _require_manager(request.user)
    company = _company(request.user)
    integrations = {
        row.supplier_id: row
        for row in SupplierIntegration.objects.filter(company=company).select_related("supplier")
    }
    suppliers = [
        {"supplier": supplier, "integration": integrations.get(supplier.pk)}
        for supplier in Supplier.objects.filter(is_active=True)
    ]
    return render(request, "app/dostawcy/integration_list.html", {
        "suppliers": suppliers,
    })


@login_required
def integration_detail(request, slug):
    _require_manager(request.user)
    company = _company(request.user)
    supplier = get_object_or_404(Supplier, slug=slug, is_active=True)
    integration = SupplierIntegration.objects.filter(company=company, supplier=supplier).first()
    if request.method == "POST":
        form = SupplierIntegrationForm(request.POST, instance=integration)
        if form.is_valid():
            integration = form.save(commit=False)
            integration.company = company
            integration.supplier = supplier
            integration.save()
            messages.success(request, "Ustawienia integracji zostały zapisane.")
            return redirect("supplier_integration_detail", slug=slug)
    else:
        form = SupplierIntegrationForm(instance=integration)
    return render(request, "app/dostawcy/integration_detail.html", {
        "supplier": supplier, "integration": integration, "form": form,
        "active_tab": request.GET.get("tab", "connection") if request.GET.get("tab") in {"connection", "prices", "stock", "sync"} else "connection",
    })


@login_required
@require_POST
def integration_sync(request, pk):
    _require_manager(request.user)
    integration = get_object_or_404(
        SupplierIntegration.objects.select_related("supplier"),
        pk=pk, company=_company(request.user),
    )
    if not integration.is_active:
        messages.error(request, "Najpierw aktywuj integrację.")
    else:
        component = request.POST.get("component") or None
        if component not in (None, "catalog", "prices", "stock"):
            raise PermissionDenied("Nieprawidłowy zakres synchronizacji.")
        SupplierIntegration.objects.filter(pk=integration.pk).update(
            last_sync_status=SupplierIntegration.SyncStatus.QUEUED,
            last_sync_error="",
        )
        sync_supplier_integration.delay(integration.pk, [component] if component else None)
        messages.success(request, "Synchronizacja została dodana do kolejki.")
    return redirect(reverse("supplier_integration_detail", kwargs={"slug": integration.supplier.slug}) + "?tab=sync")


@login_required
def supplier_catalog(request):
    company = _company(request.user)
    query = request.GET.get("q", "").strip()[:150]
    rows = SupplierCompanyProduct.objects.filter(
        company=company,
        integration__is_active=True,
        integration__supplier__is_active=True,
    ).select_related("supplier_product__supplier", "integration", "local_product")
    if query:
        rows = rows.filter(
            Q(supplier_product__name__icontains=query)
            | Q(supplier_product__sku__icontains=query)
            | Q(supplier_product__ean__icontains=query)
            | Q(supplier_product__manufacturer__icontains=query)
        )
    return render(request, "app/dostawcy/catalog.html", {"rows": rows[:100], "query": query})


@login_required
@require_POST
def supplier_product_add(request, pk):
    company = _company(request.user)
    link = get_object_or_404(
        SupplierCompanyProduct.objects.select_related("supplier_product", "local_product"),
        pk=pk, company=company, integration__is_active=True,
    )
    if link.local_product_id:
        messages.info(request, "Ten produkt jest już połączony z katalogiem firmy.")
        return redirect("supplier_catalog")
    supplier_product = link.supplier_product
    local_product = Product.objects.create(
        company=company,
        name=supplier_product.name[:255],
        sku=supplier_product.sku[:100],
        type=Product.ProductType.MATERIAL,
        unit=supplier_product.unit[:20] or "szt.",
        purchase_price=link.purchase_price_net or Decimal("0"),
        net_price=(link.purchase_price_net or Decimal("0")) * (
            Decimal("1") + (link.integration.default_markup or Decimal("0")) / Decimal("100")
        ),
        vat_rate=supplier_product.vat or Decimal("23"),
        description=supplier_product.description,
        barcode=supplier_product.ean[:100],
    )
    link.local_product = local_product
    link.save(update_fields=["local_product", "updated_at"])
    messages.success(request, "Produkt dodano do katalogu firmy. Nie dodano go do magazynu.")
    return redirect("product_detail", pk=local_product.pk)
