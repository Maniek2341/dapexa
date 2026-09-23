"""Access helpers for the service-contract (obsługa) module."""


def has_obsluga_permission(user, action):
    """Check one of the module permissions assigned directly or through a group."""
    return bool(
        getattr(user, "is_authenticated", False)
        and user.has_perm(f"obsluga.access_{action}")
    )


def can_add_obsluga(user):
    return has_obsluga_permission(user, "service_contract_add")


def can_edit_obsluga(user):
    return has_obsluga_permission(user, "service_contract_update")


def can_delete_obsluga(user):
    return has_obsluga_permission(user, "service_contract_delete")


def can_manage_obsluga(user):
    return any((can_add_obsluga(user), can_edit_obsluga(user), can_delete_obsluga(user)))
