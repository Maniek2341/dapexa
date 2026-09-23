from app.core.models import PanelUser


def can_manage_own_time_entries(user):
    return user.role in [
        PanelUser.Role.OWNER,
        PanelUser.Role.MANAGER,
        PanelUser.Role.BIURO,
    ]


def can_choose_employee_hours(user):
    return user.role in [
        PanelUser.Role.OWNER,
        PanelUser.Role.MANAGER,
        PanelUser.Role.BIURO,
    ]


def can_manage_time_requests(user):
    return user.role in [
        PanelUser.Role.OWNER,
        PanelUser.Role.MANAGER,
        PanelUser.Role.BIURO,
    ]
