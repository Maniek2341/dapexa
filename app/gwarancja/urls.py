from django.urls import path
from app.gwarancja.views import (WarrantyListView, WarrantyClaimCreateView, WarrantyDetailView, 
                              WarrantyClaimMarkReportedView, WarrantyClaimMarkRepairedView, 
                              WarrantyClaimDeleteView, WarrantyClaimUpdateView)
urlpatterns = [
    path("lista/", WarrantyListView.as_view(), name="warranty_claim_list"),
    path("add/", WarrantyClaimCreateView.as_view(), name="warranty_claim_create"),
    path("detail/<int:pk>/", WarrantyDetailView.as_view(), name="warranty_detail"),  
    path("detail/<int:pk>/mark-reported/", WarrantyClaimMarkReportedView.as_view(), name="warranty_claim_mark_reported"),
    path("detail/<int:pk>/mark-repaired/", WarrantyClaimMarkRepairedView.as_view(), name="warranty_claim_mark_repaired"),
    path("delete/<int:pk>/", WarrantyClaimDeleteView.as_view(), name="warranty_delete"),
    path("edit/<int:pk>/", WarrantyClaimUpdateView.as_view(), name="warranty_edit"),
]