from django.urls import path

from .views.offer_create_view import OfferClientLocationsView, OfferCreateView
from .views.offer_list_view import OfferListView
from .views.offer_detail_view import OfferDetailView
from .views.offer_status_update_view import OfferStatusUpdateView
from .views.offer_approve_view import OfferApproveView
from .views.offer_variant_create_view import OfferVariantCreateView
from .views.offer_variant_update_view import OfferVariantUpdateView
from .views.offer_variant_delete_view import OfferVariantDeleteView
from .views.offer_variant_toggle_selected_view import OfferVariantToggleSelectedView
from .views.offer_update_view import OfferUpdateView
from .views.offer_delete_view import OfferDeleteView
from .views.offer_priority_update_view import OfferPriorityUpdateView
from .views.offer_assign_workers_view import OfferAssignWorkersView
from .views.offer_forward_to_execution_view import OfferForwardToExecutionView

urlpatterns = [
    path("dodaj/", OfferCreateView.as_view(), name="offer_create"),
    path("lista/", OfferListView.as_view(), name="offer_list"),
    path("<int:pk>/edytuj/", OfferUpdateView.as_view(), name="offer_edit"),
    path("<int:pk>/usun/", OfferDeleteView.as_view(), name="offer_delete"),
    path("<int:pk>/przekaz-do-realizacji/", OfferForwardToExecutionView.as_view(), name="offer_forward_to_execution"),
    path("detail/<int:pk>/", OfferDetailView.as_view(), name="offer_detail"),
    path("api/client-locations/", OfferClientLocationsView.as_view(), name="offer_client_locations_api"),
    path("oferty/<int:pk>/status/", OfferStatusUpdateView.as_view(), name="offer_status_update"),
    path("oferty/<int:pk>/approve/", OfferApproveView.as_view(), name="offer_approve"),
    path("<int:offer_pk>/warianty/dodaj/", OfferVariantCreateView.as_view(), name="offer_variant_add"),
    path("wariant/<int:pk>/edytuj/", OfferVariantUpdateView.as_view(), name="offer_variant_edit"),
    path("wariant/<int:pk>/usun/", OfferVariantDeleteView.as_view(), name="offer_variant_delete"),
    path("wariant/<int:pk>/wybierz/", OfferVariantToggleSelectedView.as_view(), name="offer_variant_toggle_selected"),
    path("oferty/<int:pk>/priorytet/", OfferPriorityUpdateView.as_view(), name="offer_priority_update"),
    path("oferty/<int:pk>/pracownicy/", OfferAssignWorkersView.as_view(), name="offer_assign_workers"),

]