from django.urls import path
from app.rcp.views import (
    TimeEntryCreateView, TimeEntryListView, TimeEntryUpdateView, TimeEntryDeleteView, 
    TimeEntryRequestEditView, TimeEntryRequestMissingView, TimeEntryRequestEditSingleView, 
    TimeEntryRequestApproveView, TimeEntryRequestRejectView, TimeEntryRequestListView, TimeEntryPdfView
)

urlpatterns = [
    path("add/", TimeEntryCreateView.as_view(), name="time_entry_create"),
    path("", TimeEntryListView.as_view(), name="time_entry_list"),
    path("<int:pk>/edit/", TimeEntryUpdateView.as_view(), name="time_entry_update"),
    path("<int:pk>/delete/", TimeEntryDeleteView.as_view(), name="time_entry_delete"),
    path("request-edit/", TimeEntryRequestEditView.as_view(), name="time_entry_request_edit"),
    path("request-missing/", TimeEntryRequestMissingView.as_view(), name="time_entry_request_missing"),
    path("request-edit-single/<int:pk>/", TimeEntryRequestEditSingleView.as_view(), name="time_entry_request_edit_single"),
    path("request-approve/<int:pk>/", TimeEntryRequestApproveView.as_view(), name="time_entry_request_approve"),
    path("request-reject/<int:pk>/", TimeEntryRequestRejectView.as_view(), name="time_entry_request_reject"),
    path("request-list/", TimeEntryRequestListView.as_view(), name="time_entry_request_list"),
    path("pdf/", TimeEntryPdfView.as_view(), name="time_entry_pdf"),
]   