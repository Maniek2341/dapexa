from django.urls import path

from .views import SupportTicketCreateView, SupportTicketDetailView, SupportTicketListView, SupportTicketStatusView

urlpatterns = [
    path("", SupportTicketListView.as_view(), name="support_list"),
    path("nowe/", SupportTicketCreateView.as_view(), name="support_create"),
    path("<int:pk>/", SupportTicketDetailView.as_view(), name="support_detail"),
    path("<int:pk>/status/", SupportTicketStatusView.as_view(), name="support_status_update"),
]
