from django.urls import path

from app.pojazd.views import VehicleCreateView, VehicleListView, VehicleDetailView, VehicleEventCreateView, \
                                VehicleUpdateView, VehicleDeleteView, VehicleEventUpdateView, VehicleEventDeleteView  

urlpatterns = [
    path("dodaj/", VehicleCreateView.as_view(), name="vehicle_create"),
    path("detail<int:pk>/", VehicleDetailView.as_view(), name="vehicle_detail"),
    path("", VehicleListView.as_view(), name="vehicle_list"),
    path("edit/<int:pk>/", VehicleUpdateView.as_view(), name="vehicle_update"),
    path("<int:pk>/usun/", VehicleDeleteView.as_view(), name="vehicle_delete"),
    path("<int:vehicle_pk>/dodaj-zdarzenie/", VehicleEventCreateView.as_view(), name="vehicle_event_create"),
    path("<int:pk>/usun-zdarzenie/", VehicleEventDeleteView.as_view(), name="vehicle_event_delete"),
    path("<int:pk>/edytuj-zdarzenie/", VehicleEventUpdateView.as_view(), name="vehicle_event_update"),
]