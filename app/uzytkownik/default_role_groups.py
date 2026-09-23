from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from app.core.auth_backends import DEFAULT_ROLE_PERMISSIONS
from app.core.models import PanelUser
from app.core.view_permissions import PUBLIC_VIEW_NAMES
from app.uzytkownik.models import CompanyRoleGroup

SYSTEM_GROUP_NAMES = {
    PanelUser.Role.OWNER: "Domyślna — Właściciel",
    PanelUser.Role.MANAGER: "Domyślna — Manager",
    PanelUser.Role.BIURO: "Domyślna — Biuro",
    PanelUser.Role.PODWYKONAWCA: "Domyślna — Podwykonawca",
    PanelUser.Role.EMPLOYEE: "Domyślna — Pracownik",
    PanelUser.Role.CLIENT: "Domyślna — Klient",
}

MANAGEMENT_APP_LABELS = {
    "dokument", "gwarancja", "klient", "magazyn", "obsluga",
    "oferta_praca", "pojazd", "praca", "protokol", "rcp", "serwis",
    "sprzet", "urlop", "urzadzenie", "zadanie",
}

MANAGEMENT_CORE_CODENAMES = {
    "access_dashboard",
    "access_profile",
    "access_user_calendar",
    "access_user_calendar_events",
    "access_ajax_products",
    "access_ajax_clients",
    "access_ajax_services",
    "access_employee_add",
    "access_employee_edit",
    "access_employee_delete",
    "access_employee_list",
    "access_company_settings",
}

# Zarządzanie rolami i uprawnieniami jest dostępne również dla Biura
# (oraz Managera).
OWNER_ONLY_CODENAMES = set()


def _permissions_from_full_names(permission_names):
    query = Q(pk__in=[])
    for permission_name in permission_names:
        app_label, codename = permission_name.split(".", 1)
        query |= Q(
            content_type__app_label=app_label,
            codename=codename,
        )
    return Permission.objects.filter(query)


def get_default_permissions_for_role(role):
    if role == PanelUser.Role.OWNER:
        return Permission.objects.filter(codename__startswith="access_")

    if role in {PanelUser.Role.MANAGER, PanelUser.Role.BIURO}:
        return (
            Permission.objects
            .filter(
                Q(
                    content_type__app_label__in=MANAGEMENT_APP_LABELS,
                    codename__startswith="access_",
                )
                | Q(
                    content_type__app_label="core",
                    codename__in=MANAGEMENT_CORE_CODENAMES,
                )
            )
            .exclude(codename__in=OWNER_ONLY_CODENAMES)
            .exclude(
                codename__in=[f"access_{name}" for name in PUBLIC_VIEW_NAMES]
            )
        )

    return _permissions_from_full_names(
        DEFAULT_ROLE_PERMISSIONS.get(role, set())
    )


def ensure_default_role_groups(company):
    # Migracje uruchamiane przez Django przekazują czasem historyczną klasę
    # Company. Znormalizuj ją do bieżącej instancji, aby relacje ORM nie
    # odrzucały zapytania typu „Must be Company instance”.
    if not isinstance(company, PanelUser._meta.get_field("company").remote_field.model):
        from app.core.models import Company
        company = Company.objects.get(pk=company.pk)

    for role, display_name in SYSTEM_GROUP_NAMES.items():
        auth_group, _ = Group.objects.get_or_create(
            name=f"system-company-role:{company.pk}:{role}",
        )
        role_group, created = CompanyRoleGroup.objects.get_or_create(
            company=company,
            role=role,
            is_system=True,
            defaults={
                "name": display_name,
                "group": auth_group,
            },
        )
        default_permissions = get_default_permissions_for_role(role)
        if created:
            role_group.group.permissions.set(default_permissions)
        else:
            # Uzupełnia nowe uprawnienia w już istniejących grupach systemowych,
            # nie usuwając dodatkowych praw nadanych ręcznie.
            role_group.group.permissions.add(*default_permissions)
