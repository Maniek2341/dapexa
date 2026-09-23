from django.contrib.auth.backends import BaseBackend


EMPLOYEE_DEFAULT_PERMISSIONS = {
    "core.access_dashboard",
    "core.access_profile",
    "core.access_ajax_products",
    "klient.access_klient",
    "klient.access_klient_detail",
    "serwis.access_serwis_nowe",
    "serwis.access_serwis_detail",
    "serwis.access_service_work_log_add",
    "protokol.access_protokol_nowe",
    "protokol.access_protokol_add",
    "protokol.access_protokol_detail",
    "protokol.access_protocol_from_work",
    "protokol.access_protocol_from_service",
    "pojazd.access_vehicle_list",
    "sprzet.access_tool_list",
    "sprzet.access_tool_detail",
    "sprzet.access_tool_create",
    "sprzet.access_tool_event_add",
    "obsluga.access_service_contract_list",
    "obsluga.access_service_contract_detail",
    "urzadzenie.access_product_list",
    "gwarancja.access_warranty_claim_list",
    "gwarancja.access_warranty_detail",
    "pojazd.access_vehicle_detail",
    "pojazd.access_vehicle_event_create",
    "magazyn.access_stock_list",
    "praca.access_workorder_list",
    "praca.access_work_detail",
    "praca.access_work_status_update",
    "rcp.access_time_entry_list",
    "rcp.access_time_entry_create",
    "zadanie.access_task_complete",
    "core.access_user_calendar",
    "core.access_user_calendar_events",
    "urlop.access_urlop_add",
}

MANAGEMENT_DEFAULT_PERMISSIONS = EMPLOYEE_DEFAULT_PERMISSIONS | {
    "core.access_employee_permission_list",
    "core.access_employee_permission_edit",
    "core.access_employee_group_create",
    "core.access_employee_group_edit",
    "core.access_employee_group_delete",
    "serwis.access_serwis_add",
    "pojazd.access_vehicle_create",
    "urzadzenie.access_product_create",
    "magazyn.access_stock_item_create",
    "obsluga.access_service_contract_add",
    "zadanie.access_task_list",
    "dokument.access_documents_list",
    "oferta_praca.access_offer_list",
    "rcp.access_time_entry_request_list",
    "core.access_employee_list",
    "core.access_employee_status_toggle",
    "core.access_company_settings",
    "urlop.access_hr_leave_list",
    "urlop.access_hr_leave_cancel",
    "urlop.access_leave_type_list",
    "urlop.access_leave_allowance_list",
}

SUBCONTRACTOR_DEFAULT_PERMISSIONS = {
    "core.access_dashboard",
    "core.access_profile",
    "serwis.access_serwis_nowe",
    "zadanie.access_task_list",
    "zadanie.access_task_complete",
    "praca.access_workorder_list",
    "rcp.access_time_entry_list",
    "core.access_user_calendar",
    "core.access_user_calendar_events",
}

DEFAULT_ROLE_PERMISSIONS = {
    "employee": EMPLOYEE_DEFAULT_PERMISSIONS,
    "manager": MANAGEMENT_DEFAULT_PERMISSIONS,
    "biuro": MANAGEMENT_DEFAULT_PERMISSIONS,
    "podwykonawca": SUBCONTRACTOR_DEFAULT_PERMISSIONS,
}

PROJECT_PERMISSION_APP_LABELS = {
    "core", "dokument", "gwarancja", "klient", "magazyn", "obsluga",
    "oferta_praca", "pojazd", "praca", "protokol", "rcp", "serwis",
    "sprzet", "urlop", "urzadzenie", "zadanie", "wsparcie",
}


class RoleViewPermissionBackend(BaseBackend):
    """Provide non-removable baseline view permissions based on the user role."""

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated or not user_obj.is_active:
            return False

        try:
            app_label, codename = perm.split(".", 1)
        except ValueError:
            return False

        if not codename.startswith("access_"):
            return False

        if user_obj.role == "owner":
            return app_label in PROJECT_PERMISSION_APP_LABELS

        return perm in DEFAULT_ROLE_PERMISSIONS.get(user_obj.role, set())
