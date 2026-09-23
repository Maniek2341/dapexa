def has_work_permission(user, action):
    # Pracownik może samodzielnie zmieniać wyłącznie status pracy.
    if (
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == user.Role.EMPLOYEE
    ):
        return action == "work_status_update" and user.has_perm(
            "praca.access_work_status_update"
        )
    return bool(
        getattr(user, "is_authenticated", False)
        and user.has_perm(f"praca.access_{action}")
    )
