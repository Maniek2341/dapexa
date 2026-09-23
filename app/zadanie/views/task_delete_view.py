from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.zadanie.models import Task


class TaskDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        task = get_object_or_404(
            Task,
            pk=pk,
            company=request.user.company,
        )

        task.delete()

        messages.success(request, "Zadanie zostało usunięte.")

        return redirect(
            request.META.get("HTTP_REFERER", "task_list")
        )