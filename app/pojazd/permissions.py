def can_edit_vehicle(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and user.has_perm("pojazd.access_vehicle_update")
    )


def can_create_vehicle(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and user.has_perm("pojazd.access_vehicle_create")
    )


def can_delete_vehicle(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and user.has_perm("pojazd.access_vehicle_delete")
    )
