def can_view_product_detail(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) != user.Role.EMPLOYEE
        and user.has_perm("urzadzenie.access_product_detail")
    )


def can_create_product(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) != user.Role.EMPLOYEE
        and user.has_perm("urzadzenie.access_product_create")
    )
