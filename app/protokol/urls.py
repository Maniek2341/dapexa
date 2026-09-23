from django.urls import path

from app.protokol.views import (ProtokolNoweView, ProtokolDetailView, ProtokolAddView, ProtocolStatusUpdateView, ProtocolMediaDeleteView, 
ProtocolDeleteView, ProtocolEditView, ProtocolFromServiceView, ProtocolPDFView,ProtocolFromWorkView)

urlpatterns = [
    path('', ProtokolNoweView.as_view(), name='protokol_nowe'),
    path('add', ProtokolAddView.as_view(), name='protokol_add'),
    path("protokol/<int:pk>/", ProtokolDetailView.as_view(), name="protokol_detail"),
    path("protocol/<int:pk>/status/", ProtocolStatusUpdateView.as_view(), name="protocol_change_status"),
    path("media/<int:pk>/delete/", ProtocolMediaDeleteView.as_view(), name="protocol_media_delete",),
    path("protokol/<int:pk>/usun/", ProtocolDeleteView.as_view(), name="protocol_delete"),
    path("protokol/<int:pk>/edytuj/", ProtocolEditView.as_view(), name="protocol_edit"),
    path("serwis/<int:pk>/stworz-protokol/", ProtocolFromServiceView.as_view(), name="protocol_from_service"),
    path("pdf/<int:pk>/", ProtocolPDFView.as_view(), name="protocol_pdf"),
    path("work/<int:pk>/create-protocol/", ProtocolFromWorkView.as_view(), name="protocol_from_work"),
]