from django.urls import path

from app.zadanie.views import TaskListView, TaskCreateView, TaskDeleteView, TaskCompleteView

urlpatterns = [
    path("", TaskListView.as_view(), name="task_list"),
    path("add/", TaskCreateView.as_view(), name="task_create"),
    path("<int:pk>/complete/", TaskCompleteView.as_view(), name="task_complete"),
    path("<int:pk>/delete/", TaskDeleteView.as_view(), name="task_delete"),
]
