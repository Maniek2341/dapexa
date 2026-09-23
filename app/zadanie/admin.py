from django import forms
from django.contrib import admin
from .models import Task


class TaskAdminForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        at = cleaned.get("assignment_type")

        if at == Task.AssignmentType.USER and not cleaned.get("assigned_user"):
            raise forms.ValidationError("Dla 'Jedna osoba' musisz wybrać użytkownika.")

        if at == Task.AssignmentType.ROLE and not cleaned.get("assigned_role"):
            raise forms.ValidationError("Dla 'Rola' musisz wybrać rolę.")

        return cleaned


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    form = TaskAdminForm
    list_display = ("title", "company", "assignment_type", "assigned_user", "assigned_role", "due_date", "status")
    list_filter = ("company", "assignment_type", "assigned_role", "status")
    search_fields = ("title", "assigned_user__username")
    readonly_fields = ("created_at", "updated_at")
