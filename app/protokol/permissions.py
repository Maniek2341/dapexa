"""Permission helpers for protocol views."""


def can_manage_protocols(user):
    """Return whether the user may edit or delete protocols.

    Employees have read-only access to the protocol list.  Other authenticated
    roles retain the existing management capabilities.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    return any(
        user.has_perm(f"protokol.access_{action}")
        for action in (
            "protokol_add", "protocol_edit", "protocol_delete",
            "protocol_change_status", "protocol_media_delete",
        )
    )
