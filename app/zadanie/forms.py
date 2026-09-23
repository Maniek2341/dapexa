from django import forms
from django.contrib.auth import get_user_model

from .models import Task


User = get_user_model()


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "description",
            "assignment_type",
            "assigned_user",
            "assigned_role",
            "due_date",
            "status",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "assignment_type": forms.Select(attrs={"class": "form-select", "id": "id_assignment_type"}),
            "assigned_user": forms.Select(attrs={"class": "form-select", "id": "id_assigned_user"}),
            "assigned_role": forms.Select(attrs={"class": "form-select", "id": "id_assigned_role"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["assigned_user"].required = False
        self.fields["assigned_role"].required = False

        if self.request_user and self.request_user.company:
            self.fields["assigned_user"].queryset = User.objects.filter(
                company=self.request_user.company
            )
        else:
            self.fields["assigned_user"].queryset = User.objects.none()

    def clean(self):
        cleaned_data = super().clean()

        assignment_type = cleaned_data.get("assignment_type")
        assigned_user = cleaned_data.get("assigned_user")
        assigned_role = cleaned_data.get("assigned_role")

        if assignment_type == Task.AssignmentType.USER and not assigned_user:
            self.add_error("assigned_user", "Wybierz osobę.")

        if assignment_type == Task.AssignmentType.ROLE and not assigned_role:
            self.add_error("assigned_role", "Wybierz rolę.")

        if assignment_type == Task.AssignmentType.ALL:
            cleaned_data["assigned_user"] = None
            cleaned_data["assigned_role"] = None

        if assignment_type == Task.AssignmentType.USER:
            cleaned_data["assigned_role"] = None

        if assignment_type == Task.AssignmentType.ROLE:
            cleaned_data["assigned_user"] = None

        return cleaned_data