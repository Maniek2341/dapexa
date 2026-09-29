from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from app.core.models import Company, PanelUser
from app.pojazd.permissions import can_create_vehicle
from app.pojazd.views.vehicle_create_view import VehicleCreateView


class VehicleCreatePermissionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Firma pojazdy")
        self.employee = PanelUser.objects.create_user(
            email="employee-vehicle@example.test",
            password="test-password",
            company=self.company,
            role=PanelUser.Role.EMPLOYEE,
        )
        self.factory = RequestFactory()

    def test_employee_needs_add_permission_and_can_create_vehicle_when_granted(self):
        self.assertFalse(can_create_vehicle(self.employee))

        request = self.factory.get("/pojazd/dodaj/")
        request.user = self.employee
        with self.assertRaises(PermissionDenied):
            VehicleCreateView.as_view()(request)

        permission = Permission.objects.get(
            content_type__app_label="pojazd",
            codename="access_vehicle_create",
        )
        self.employee.user_permissions.add(permission)
        self.employee = PanelUser.objects.get(pk=self.employee.pk)
        self.assertTrue(can_create_vehicle(self.employee))

        request = self.factory.get("/pojazd/dodaj/")
        request.user = self.employee
        response = VehicleCreateView.as_view()(request)
        self.assertEqual(response.status_code, 200)
