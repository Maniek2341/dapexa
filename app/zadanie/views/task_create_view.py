from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView

from app.zadanie.models import Task
from app.zadanie.forms import TaskForm


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "app/zadanie/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        task = form.save(commit=False)
        task.company = self.request.user.company
        task.created_by = self.request.user
        task.save()

        messages.success(self.request, "Zadanie zostało dodane.")
        return redirect("task_list")
