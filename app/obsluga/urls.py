from django.urls import path

from app.obsluga.views import ServiceContractListView, ServiceContractCreateView, ServiceContractDetailView, \
    ServiceContractUpdateView, ServiceContractAssetCreateView, ServiceContractParameterCreateView, \
    ServiceContractAssetUpdateView, ServiceContractAssetDeleteView, ServiceContractParameterUpdateView, \
    ServiceContractParameterDeleteView, ServiceVisitConfirmPeriodView, ServiceContractDeleteView

urlpatterns = [
    path('service_contracts/', ServiceContractListView.as_view(), name='service_contract_list'),
    path('service_contracts/add/', ServiceContractCreateView.as_view(), name='service_contract_add'),
    path('service_contracts/<int:pk>/', ServiceContractDetailView.as_view(), name='service_contract_detail'),
    path("service_contracts/<int:pk>/assets/add/", ServiceContractAssetCreateView.as_view(), name="service_contract_asset_add"),
    path("service_contracts/<int:contract_pk>/assets/<int:asset_pk>/edit/", ServiceContractAssetUpdateView.as_view(), name="service_contract_asset_update"),
    path("service_contracts/<int:contract_pk>/assets/<int:asset_pk>/delete/", ServiceContractAssetDeleteView.as_view(), name="service_contract_asset_delete"),
    path("service_contracts/<int:pk>/parameters/add/", ServiceContractParameterCreateView.as_view(), name="service_contract_parameter_add"),
    path("service_contracts/<int:pk>/edit/", ServiceContractUpdateView.as_view(), name="service_contract_update"),
    path("service_contracts/<int:contract_pk>/parameters/<int:parameter_pk>/edit/", ServiceContractParameterUpdateView.as_view(), name="service_contract_parameter_update"),
    path("service_contracts/<int:contract_pk>/parameters/<int:parameter_pk>/delete/", ServiceContractParameterDeleteView.as_view(), name="service_contract_parameter_delete"),
    path("service_contracts/<int:pk>/confirm-period/", ServiceVisitConfirmPeriodView.as_view(), name="service_visit_confirm_period"),
    path("service_contracts/<int:pk>/delete/", ServiceContractDeleteView.as_view(), name="service_contract_delete"),
]
