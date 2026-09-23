from django.urls import path

from app.urzadzenie.views import ProductCreateView, ProductListView, ProductDetailView, ProductOfferUsageView, \
ProductProtocolUsageView, ProductStockHistoryView, ProductUpdateView

urlpatterns = [
    path("dodaj/", ProductCreateView.as_view(), name="product_create"),
    path("", ProductListView.as_view(), name="product_list"),
    path("detail/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("<int:pk>/uzycie/oferty/", ProductOfferUsageView.as_view(), name="product_offer_usage",),
    path("<int:pk>/uzycie/protokoly/", ProductProtocolUsageView.as_view(), name="product_protocol_usage",),
    path("<int:pk>/magazyn/historia/", ProductStockHistoryView.as_view(), name="product_stock_history",),
    path('<int:pk>/edytuj/', ProductUpdateView.as_view(), name='product_update'),
]