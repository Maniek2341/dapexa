def can_manage_stock(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) != user.Role.EMPLOYEE
        and any(user.has_perm(f"magazyn.access_{name}") for name in ("stock_item_create", "stock_in", "stock_out"))
    )
