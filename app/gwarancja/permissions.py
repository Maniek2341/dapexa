def can_delete_warranty(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and user.has_perm("gwarancja.access_warranty_delete")
    )

def can_edit_warranty(user):
    return bool(getattr(user, "is_authenticated", False) and user.has_perm("gwarancja.access_warranty_edit"))
