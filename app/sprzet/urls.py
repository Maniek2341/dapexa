from django.urls import path

from app.sprzet.views import ToolListView, ToolCreateView, ToolDetailView, ToolEventAddView, ToolUpdateView, ToolDeleteView

urlpatterns = [
    path("", ToolListView.as_view(), name="tool_list"),
    path("add/", ToolCreateView.as_view(), name="tool_create"),
    path("<int:pk>/", ToolDetailView.as_view(), name="tool_detail"),
    path("<int:pk>/event/add/", ToolEventAddView.as_view(), name="tool_event_add"),
    path("<int:pk>/edit/", ToolUpdateView.as_view(), name="tool_update"),
    path("<int:pk>/delete/", ToolDeleteView.as_view(), name="tool_delete"),
]