def can_manage_services(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return any(
        user.has_perm(f"serwis.access_{action}")
        for action in (
            "serwis_add", "serwis_edit", "serwis_delete", "serwis_status_update",
            "serwis_schedule_update", "serwis_assign_workers", "service_note_add",
            "service_note_pin", "service_note_delete", "service_media_delete",
            "serwis_priority_update", "serwis_status_zgrania_update",
        )
    )
