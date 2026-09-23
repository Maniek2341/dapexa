def can_manage_clients(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return any(
        user.has_perm(f"klient.access_{action}")
        for action in (
            "klient_add", "klient_edit", "klient_delete", "klient_deactivate",
            "klient_activate", "client_note_pin", "client_note_delete",
            "contact_person_add", "location_add", "location_edit", "location_delete",
        )
    )
