from django.urls import path


from app.klient.views import (KlientView, KlientAddView, KlientDetailView, KlientEditView, KlientDeleteView, KlientDeactivateView, 
KlientArchiveView, KlientActivateView, ClientNoteTogglePinView, ClientNoteDeleteView, ContactPersonAddView, LocationAddView, 
LocationDeleteView, LocationEditView)

urlpatterns = [
    path('', KlientView.as_view(), name='klient'),
    path('add', KlientAddView.as_view(), name='klient_add'),
    path('edit/<int:pk>/', KlientEditView.as_view(), name='klient_edit'),
    path('detail/<int:pk>/', KlientDetailView.as_view(), name='klient_detail'),
    path('delete/<int:pk>/', KlientDeleteView.as_view(), name='klient_delete'),
    path('deactivate/<int:pk>/', KlientDeactivateView.as_view(), name='klient_deactivate'),
    path('archive', KlientArchiveView.as_view(), name='klient_archive'),
    path('activate/<int:pk>/', KlientActivateView.as_view(), name='klient_activate'),
    path('note/toggle-pin/<int:pk>/', ClientNoteTogglePinView.as_view(), name='client_note_pin'),
    path('note/delete/<int:pk>/', ClientNoteDeleteView.as_view(), name='client_note_delete'),
    path('contact-person/add/<int:client_pk>/', ContactPersonAddView.as_view(), name='contact_person_add'),
    path('klient/<int:client_id>/lokalizacja/dodaj/', LocationAddView.as_view(), name='location_add'),
    path('lokalizacja/<int:location_id>/edytuj/', LocationEditView.as_view(), name='location_edit'),
    path('lokalizacja/<int:location_id>/usun/', LocationDeleteView.as_view(), name='location_delete'),
]