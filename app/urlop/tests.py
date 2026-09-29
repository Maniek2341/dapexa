from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client as HttpClient, TestCase
from django.urls import reverse
from django.utils import timezone

from app.core.models import Company, PanelUser, Subscription
from app.klient.models import Client
from app.rcp.models import TimeEntry, TimeEntryRequest
from app.urlop.allowance_generator import ensure_allowance, ensure_year_allowances
from app.urlop.forms import LeaveRequestForm, LeaveTypeForm
from app.urlop.models import LeaveAllowance, LeaveRequest, LeaveType, LeavePool
from app.urlop.services import get_remaining_days, used_vacation_days


class LeaveModuleTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma A")
        self.other_company = Company.objects.create(name="Firma B")
        self.owner = self.make_user("owner", self.company)
        self.manager = self.make_user("manager", self.company)
        self.employee = self.make_user("employee", self.company)
        self.foreign_employee = self.make_user("employee", self.other_company)
        for company, owner in ((self.company, self.owner), (self.other_company, self.make_user("owner", self.other_company))):
            Subscription.objects.create(
                company=company, owner=owner, package=Subscription.Package.PRO,
                status=Subscription.STATUS_ACTIVE,
            )
        self.vacation = LeaveType.objects.create(
            company=self.company, name="Wypoczynkowy", code="vacation",
            pool=LeavePool.VACATION, annual_limit_days=26,
        )
        self.foreign_type = LeaveType.objects.create(
            company=self.other_company, name="Obcy", code="vacation",
            pool=LeavePool.VACATION, annual_limit_days=26,
        )
        self.allowance = LeaveAllowance.objects.create(
            company=self.company, user=self.employee, year=2026,
            vacation_limit=Decimal("20"), carryover_days=Decimal("3"),
            adjustment_days=Decimal("1"), carryover_deadline=date(2026, 9, 30),
        )
        self.client.force_login(self.owner, backend="django.contrib.auth.backends.ModelBackend")

    def make_user(self, role, company):
        suffix = PanelUser.objects.count()
        return PanelUser.objects.create_user(
            email=f"{role}-{company.pk}-{suffix}@leave.test", password="test-password",
            company=company, role=role,
        )

    def make_leave(self, *, user=None, leave_type=None, start=date(2026, 3, 2), end=None,
                   status=LeaveRequest.Status.SUBMITTED, carryover=False, company=None,
                   approver=None):
        user = user or self.employee
        leave_type = leave_type or self.vacation
        end = end or start
        if status == LeaveRequest.Status.APPROVED and approver is None:
            approver = self.owner if user.company_id == self.company.pk else PanelUser.objects.get(
                company=user.company, role=PanelUser.Role.OWNER,
            )
        return LeaveRequest.objects.create(
            company=company or user.company, user=user, leave_type=leave_type,
            date_from=start, date_to=end, leave_year=start.year,
            days_count=Decimal("0"), is_carryover=carryover, status=status,
            approver=approver,
            approved_at=timezone.now() if status == LeaveRequest.Status.APPROVED else None,
        )

    def leave_form(self, start="2026-03-02", end="2026-03-02", **extra):
        return LeaveRequestForm(
            data={"leave_type": self.vacation.pk, "date_from": start, "date_to": end, **extra},
            user=self.employee,
        )

    def test_days_exclude_weekends_and_polish_holidays(self):
        form = self.leave_form("2026-04-03", "2026-04-07")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["days_count_calc"], Decimal("2"))

    def test_form_rejects_over_limit_and_missing_allowance_cleanly(self):
        self.allowance.vacation_limit = Decimal("1")
        self.allowance.carryover_days = Decimal("0")
        self.allowance.adjustment_days = Decimal("0")
        self.allowance.save()
        self.make_leave(status=LeaveRequest.Status.APPROVED)
        form = self.leave_form("2026-03-03", "2026-03-04")
        self.assertFalse(form.is_valid())
        self.assertIn("limit", str(form.errors).lower())
        self.allowance.delete()
        self.assertFalse(self.leave_form().is_valid())

    def test_overlapping_submitted_or_approved_leave_is_rejected(self):
        self.make_leave()
        self.assertFalse(self.leave_form().is_valid())
        self.make_leave(start=date(2026, 3, 4), status=LeaveRequest.Status.REJECTED)
        later_form = self.leave_form("2026-03-04", "2026-03-04")
        self.assertTrue(later_form.is_valid(), later_form.errors)

    def test_cross_year_leave_is_split_between_years(self):
        LeaveAllowance.objects.create(company=self.company, user=self.employee, year=2027, vacation_limit=20)
        form = self.leave_form("2026-12-31", "2027-01-04")
        self.assertTrue(form.is_valid(), form.errors)
        leave = self.make_leave(start=date(2026, 12, 31), end=date(2027, 1, 4), status=LeaveRequest.Status.APPROVED)
        self.assertEqual(leave.days_count, Decimal("2"))
        self.assertEqual(used_vacation_days(self.company, self.employee, 2026), Decimal("1"))
        self.assertEqual(used_vacation_days(self.company, self.employee, 2027), Decimal("1"))

    def test_approved_consumes_balance_but_rejected_and_cancelled_do_not(self):
        self.make_leave(status=LeaveRequest.Status.REJECTED)
        self.make_leave(start=date(2026, 3, 3), status=LeaveRequest.Status.CANCELLED)
        approved = self.make_leave(start=date(2026, 3, 4), status=LeaveRequest.Status.APPROVED, approver=self.owner)
        self.assertEqual(used_vacation_days(self.company, self.employee, 2026), Decimal("1"))
        self.assertEqual(get_remaining_days(self.company, self.employee, 2026), Decimal("23"))
        self.assertIsNotNone(approved.approved_at)

    def test_carryover_has_separate_limit_and_deadline(self):
        self.allowance.vacation_limit = Decimal("20")
        self.allowance.carryover_days = Decimal("0")
        self.allowance.save()
        self.assertFalse(self.leave_form("2026-03-02", is_carryover="on").is_valid())
        self.allowance.carryover_days = Decimal("1")
        self.allowance.save()
        self.assertTrue(self.leave_form("2026-03-02", is_carryover="on").is_valid())
        self.assertFalse(self.leave_form("2026-10-01", is_carryover="on").is_valid())

    def test_unlimited_type_never_consumes_vacation_pool(self):
        unlimited = LeaveType.objects.create(
            company=self.company, name="Bez limitu", code="unlimited",
            pool=LeavePool.VACATION, counts_against_limit=False, annual_limit_days=0,
        )
        self.make_leave(leave_type=unlimited, status=LeaveRequest.Status.APPROVED)
        self.assertEqual(used_vacation_days(self.company, self.employee, 2026), Decimal("0"))

    def test_approval_and_rejection_are_post_only_and_only_pending_once(self):
        leave = self.make_leave()
        approve_url = reverse("hr_leave_approve", args=[leave.pk])
        self.assertEqual(self.client.get(approve_url).status_code, 405)
        self.assertEqual(self.client.post(approve_url).status_code, 302)
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(leave.approver_id, self.owner.pk)
        self.assertIsNotNone(leave.approved_at)
        self.assertEqual(self.client.post(approve_url).status_code, 302)
        self.client.post(reverse("hr_leave_cancel", args=[leave.pk]))
        self.assertEqual(self.client.post(approve_url).status_code, 302)
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.CANCELLED)

    def test_employee_cannot_approve_and_cannot_cancel_others(self):
        leave = self.make_leave(user=self.manager)
        self.client.force_login(self.employee, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(self.client.post(reverse("hr_leave_approve", args=[leave.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("my_leave_cancel", args=[leave.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("leave_type_list")).status_code, 403)

    def test_client_cannot_manage_leave_or_read_allowances(self):
        client_user = self.make_user(PanelUser.Role.CLIENT, self.company)
        self.client.force_login(client_user, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(self.client.get(reverse("leave_allowance_list")).status_code, 403)
        self.assertEqual(self.client.post(reverse("leave_type_edit", args=[self.vacation.pk]), {}).status_code, 403)

    def test_foreign_ids_are_hidden_from_hr_endpoints_and_calendar(self):
        foreign = self.make_leave(
            user=self.foreign_employee, leave_type=self.foreign_type,
            status=LeaveRequest.Status.APPROVED, approver=self.make_user("owner", self.other_company),
            company=self.other_company,
        )
        for name in ("hr_leave_approve", "hr_leave_reject"):
            self.assertEqual(self.client.post(reverse(name, args=[foreign.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("hr_leave_pdf", args=[foreign.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("hr_leave_cancel", args=[foreign.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("hr_leave_list")), self.foreign_employee.email)

    def test_calendar_hides_other_requests_details_and_nonapproved_statuses(self):
        self.make_leave(user=self.manager, status=LeaveRequest.Status.APPROVED, approver=self.owner)
        self.make_leave(user=self.manager, start=date(2026, 3, 3), status=LeaveRequest.Status.CANCELLED)
        self.make_leave(user=self.employee, start=date(2026, 3, 4), status=LeaveRequest.Status.CANCELLED)
        self.client.force_login(self.employee, backend="django.contrib.auth.backends.ModelBackend")
        events = self.client.get(reverse("user_calendar_events")).json()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "Nieobecność")

    def test_limits_are_idempotent_and_preserve_hr_adjustments(self):
        self.allowance.is_locked = True
        self.allowance.adjustment_days = Decimal("2")
        self.allowance.save()
        ensure_year_allowances(self.company, 2026)
        self.assertEqual(ensure_year_allowances(self.company, 2026), 0)
        self.allowance.refresh_from_db()
        self.assertEqual(self.allowance.adjustment_days, Decimal("2"))
        self.assertTrue(self.allowance.is_locked)
        self.assertEqual(LeaveAllowance.objects.filter(company=self.company, user=self.employee, year=2026).count(), 1)

    def test_allowance_calculation_matches_part_time_and_hire_year(self):
        self.employee.employment_fraction = Decimal("0.5")
        self.employee.employment_start_date = date(2026, 7, 1)
        self.employee.save()
        self.allowance.delete()
        allowance = ensure_allowance(self.company, self.employee, 2026)
        self.assertEqual(allowance.vacation_limit, self.employee.get_vacation_entitlement(as_of=date(2026, 12, 31)))

    def test_employee_without_configured_leave_type_gets_selectable_vacation_and_auto_limit(self):
        company = Company.objects.create(name="Firma bez konfiguracji urlopów")
        employee = self.make_user("employee", company)
        form = LeaveRequestForm(
            data={"date_from": "2026-03-02", "date_to": "2026-03-02"},
            user=employee,
        )

        vacation_type = form.fields["leave_type"].queryset.get(pool=LeavePool.VACATION)
        form.data = {**form.data, "leave_type": str(vacation_type.pk)}
        self.assertTrue(form.is_valid(), form.errors)
        allowance = LeaveAllowance.objects.get(company=company, user=employee, year=2026)
        self.assertEqual(allowance.vacation_limit, employee.get_vacation_entitlement(as_of=date(2026, 12, 31)))

    def test_leave_type_form_requires_pool_and_prevents_duplicate_codes(self):
        form = LeaveTypeForm(data={
            "name": "Other", "code": "VACATION", "pool": "other",
            "counts_against_limit": "on", "annual_limit_days": "2",
        }, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)

    def test_used_leave_type_cannot_have_its_rules_rewritten(self):
        self.make_leave()
        form = LeaveTypeForm(data={
            "name": self.vacation.name, "code": "different", "pool": "other",
            "counts_against_limit": "on", "annual_limit_days": "26",
        }, instance=self.vacation, company=self.company)
        self.assertFalse(form.is_valid())

    def test_approved_leave_cannot_be_edited_through_model(self):
        leave = self.make_leave(status=LeaveRequest.Status.APPROVED, approver=self.owner)
        leave.date_to = date(2026, 3, 31)
        with self.assertRaises(ValidationError):
            leave.save()

    def test_rcp_approval_is_blocked_on_approved_leave(self):
        from django.core.exceptions import ValidationError as DjangoValidationError
        self.make_leave(status=LeaveRequest.Status.APPROVED, approver=self.owner)
        time_request = TimeEntryRequest.objects.create(
            company=self.company, user=self.employee, request_type="missing",
            date=date(2026, 3, 2), new_start_time=time(8), new_end_time=time(16), reason="RCP",
        )
        with self.assertRaises(DjangoValidationError):
            time_request.approve(self.owner)
        self.assertFalse(TimeEntry.objects.filter(user=self.employee, date=date(2026, 3, 2)).exists())
