from django.urls import path

from app.serwis.views import (SerwisNoweView, SerwisDetailView, SerwisAddView, ServiceNoteAddView,
ServiceNoteDeleteView, ServiceNotePinView, SerwisEditView, SerwisDeleteView, SerwisStatusUpdateView, SerwisScheduleUpdateView, 
SerwisAssignWorkersView, ServiceMediaDeleteView, SerwisPriorityUpdateView, SerwisStatusZgraniaUpdateView,
ServiceWorkLogCreateView)

from app.serwis.views import client_locations_api

urlpatterns = [
    path('', SerwisNoweView.as_view(), name='serwis_nowe'),
    path('add', SerwisAddView.as_view(), name='serwis_add'),
    path('detail/<int:pk>', SerwisDetailView.as_view(), name='serwis_detail'),
    path('detail/<int:pk>/work-log/add/', ServiceWorkLogCreateView.as_view(), name='service_work_log_add'),
    path("serwis/<int:pk>/note/add/", ServiceNoteAddView.as_view(), name="service_note_add"),
    path("serwis/note/<int:note_pk>/pin/", ServiceNotePinView.as_view(), name="service_note_pin"),
    path("serwis/note/<int:note_pk>/delete/", ServiceNoteDeleteView.as_view(), name="service_note_delete"),
    path("serwis/edit/<int:pk>/", SerwisEditView.as_view(), name="serwis_edit"),
    path("serwis/delete/<int:pk>/", SerwisDeleteView.as_view(), name="serwis_delete"),
    path("serwis/<int:pk>/status/", SerwisStatusUpdateView.as_view(), name="serwis_status_update"),
    path("serwis/<int:pk>/schedule/", SerwisScheduleUpdateView.as_view(), name="serwis_schedule_update"),
    path("serwis/<int:pk>/assign-workers/", SerwisAssignWorkersView.as_view(), name="serwis_assign_workers"),
    path("media/<int:pk>/delete/", ServiceMediaDeleteView.as_view(), name="service_media_delete"),
    path("serwis/<int:pk>/priority/", SerwisPriorityUpdateView.as_view(), name="serwis_priority_update"),
    path("serwis/<int:pk>/status-zgrania/", SerwisStatusZgraniaUpdateView.as_view(), name="serwis_status_zgrania_update"),
    # urls.py
    path("api/client-locations/", client_locations_api, name="client_locations_api"),
]
