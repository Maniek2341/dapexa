from django.urls import path

from app.magazyn.views import (
    StockListView,
    StockItemCreateView,
    StockInView,
    StockOutView,
    WarehouseCreateView,
)

urlpatterns = [
    path("", StockListView.as_view(), name="stock_list"),
    path("add/", StockItemCreateView.as_view(), name="stock_item_create"),
    path("warehouse/add/", WarehouseCreateView.as_view(), name="warehouse_create"),
    path("<int:pk>/in/", StockInView.as_view(), name="stock_in"),
    path("<int:pk>/out/", StockOutView.as_view(), name="stock_out"),
]
