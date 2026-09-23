from django.urls import path

from app.praca.views import WorkOrderListView, WorkDetailView, WorkAssignWorkersView, WorkScheduleUpdateView, \
                            WorkMarkOrderedView, WorkStatusUpdateView

urlpatterns = [
    path("", WorkOrderListView.as_view(), name="workorder_list"),
    path("<int:pk>/", WorkDetailView.as_view(), name="work_detail"),
    path("<int:pk>/assign-workers/", WorkAssignWorkersView.as_view(), name="work_assign_workers"),
    path("<int:pk>/schedule/", WorkScheduleUpdateView.as_view(), name="work_schedule_update"),
    path("<int:pk>/mark-ordered/", WorkMarkOrderedView.as_view(), name="work_mark_ordered"),
    path("<int:pk>/status/", WorkStatusUpdateView.as_view(), name="work_status_update"),
]