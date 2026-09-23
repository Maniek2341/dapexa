import datetime

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from app.core.models import Company, PanelUser, Subscription
from app.zadanie.models import Task
from app.zadanie.views import TaskCompleteView


class TaskCompleteViewTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma testowa")
        self.user = PanelUser.objects.create_user(
            email="employee@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.EMPLOYEE,
        )
        self.other_user = PanelUser.objects.create_user(
            email="other@example.com",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.EMPLOYEE,
        )
        Subscription.objects.create(
            company=self.company,
            owner=self.user,
            status=Subscription.STATUS_ACTIVE,
            package=Subscription.Package.STANDARD,
        )

    def test_assigned_user_can_mark_task_done(self):
        task = Task.objects.create(
            company=self.company,
            title="Zadanie testowe",
            assignment_type=Task.AssignmentType.USER,
            assigned_user=self.user,
            due_date=timezone.localdate() - datetime.timedelta(days=1),
        )

        self.client.force_login(
            self.user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        response = self.client.post(reverse("task_complete", kwargs={"pk": task.pk}))

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)
        self.assertFalse(task.is_overdue)

    def test_user_cannot_mark_unassigned_task_done(self):
        task = Task.objects.create(
            company=self.company,
            title="Cudze zadanie",
            assignment_type=Task.AssignmentType.USER,
            assigned_user=self.other_user,
        )
        request = RequestFactory().post(reverse("task_complete", kwargs={"pk": task.pk}))
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            TaskCompleteView.as_view()(request, pk=task.pk)

        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.OPEN)
