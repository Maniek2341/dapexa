from django.urls import path

from . import views

urlpatterns = [
    path("", views.integration_list, name="supplier_integrations"),
    path("katalog/", views.supplier_catalog, name="supplier_catalog"),
    path("<int:pk>/synchronizuj/", views.integration_sync, name="supplier_integration_sync"),
    path("produkt/<int:pk>/dodaj/", views.supplier_product_add, name="supplier_product_add"),
    path("<slug:slug>/", views.integration_detail, name="supplier_integration_detail"),
]
