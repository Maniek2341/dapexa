def can_edit_tool(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) != user.Role.EMPLOYEE
        and user.has_perm("sprzet.access_tool_update")
    )


def can_delete_tool(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) != user.Role.EMPLOYEE
        and user.has_perm("sprzet.access_tool_delete")
    )
