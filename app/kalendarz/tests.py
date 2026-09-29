from django.test import TestCase
from django.urls import reverse

from app.core.models import Company, PanelUser, Subscription
from app.kalendarz.models import Event


class PersonalCalendarSharingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma kalendarza")
        self.other_company = Company.objects.create(name="Inna firma kalendarza")
        self.owner = self.make_user("owner", self.company)
        self.employee = self.make_user("employee", self.company)
        self.foreign_employee = self.make_user("foreign", self.other_company)
        Subscription.objects.create(
            company=self.company,
            owner=self.owner,
            package=Subscription.Package.STANDARD,
            status=Subscription.STATUS_ACTIVE,
        )

    def make_user(self, prefix, company):
        return PanelUser.objects.create_user(
            email=f"{prefix}-{company.pk}@calendar.test",
            password="test-password",
            company=company,
            role=PanelUser.Role.OWNER if prefix == "owner" else PanelUser.Role.EMPLOYEE,
        )

    def add_event(self):
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")
        return self.client.post(
            reverse("calendar_personal_event_add"),
            {
                "title": "Spotkanie zespołu",
                "description": "Wspólny wpis",
                "start": "2026-06-02T10:00",
                "end": "2026-06-02T11:00",
                "attendees": [str(self.employee.pk), str(self.foreign_employee.pk)],
            },
        )

    def test_event_can_be_shared_only_with_users_from_same_company(self):
        response = self.add_event()
        self.assertEqual(response.status_code, 302)

        event = Event.objects.get(title="Spotkanie zespołu")
        self.assertEqual(event.created_by, self.owner)
        self.assertSetEqual(
            set(event.attendees.values_list("pk", flat=True)),
            {self.owner.pk, self.employee.pk},
        )

        self.client.force_login(self.employee, backend="django.contrib.auth.backends.ModelBackend")
        events = self.client.get(reverse("user_calendar_events")).json()
        self.assertTrue(any(item["title"] == event.title for item in events))

    def test_recipient_cannot_delete_another_persons_shared_event(self):
        self.add_event()
        event = Event.objects.get(title="Spotkanie zespołu")
        self.client.force_login(self.employee, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.post(reverse("calendar_personal_event_delete", args=[event.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Event.objects.filter(pk=event.pk).exists())

    def test_author_can_delete_shared_event(self):
        self.add_event()
        event = Event.objects.get(title="Spotkanie zespołu")
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.post(reverse("calendar_personal_event_delete", args=[event.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(pk=event.pk).exists())

    def test_author_can_change_shares_of_existing_event(self):
        self.add_event()
        event = Event.objects.get(title="Spotkanie zespołu")
        replacement = self.make_user("replacement", self.company)
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.post(
            reverse("calendar_personal_event_share", args=[event.pk]),
            {"attendees": [str(replacement.pk), str(self.foreign_employee.pk)]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertSetEqual(
            set(event.attendees.values_list("pk", flat=True)),
            {self.owner.pk, replacement.pk},
        )

    def test_recipient_cannot_change_shares(self):
        self.add_event()
        event = Event.objects.get(title="Spotkanie zespołu")
        self.client.force_login(self.employee, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.post(
            reverse("calendar_personal_event_share", args=[event.pk]),
            {"attendees": [str(self.foreign_employee.pk)]},
        )

        self.assertIn(response.status_code, (403, 404))
        self.assertSetEqual(
            set(event.attendees.values_list("pk", flat=True)),
            {self.owner.pk, self.employee.pk},
        )

    def test_weekend_event_is_rejected(self):
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.post(
            reverse("calendar_personal_event_add"),
            {"title": "Weekend", "start": "2026-06-06T10:00", "end": "2026-06-06T11:00"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(title="Weekend").exists())

    def test_daily_recurrence_is_returned_on_weekdays_only(self):
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")
        self.client.post(
            reverse("calendar_personal_event_add"),
            {
                "title": "Codzienne spotkanie",
                "start": "2026-06-01T10:00",
                "end": "2026-06-01T11:00",
                "recurrence": Event.Recurrence.DAILY,
                "recurrence_until": "2026-06-07",
            },
        )

        events = self.client.get(
            reverse("user_calendar_events"),
            {"start": "2026-06-01T00:00", "end": "2026-06-08T00:00"},
        ).json()
        occurrences = [item for item in events if item["title"] == "Codzienne spotkanie"]

        self.assertEqual(len(occurrences), 5)
        self.assertEqual(
            [item["start"][:10] for item in occurrences],
            ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"],
        )
