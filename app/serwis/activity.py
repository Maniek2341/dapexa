from app.serwis.models import ServiceActivity


def log_service_activity(*, company, service, type, title="", description="", user=None):
    return ServiceActivity.objects.create(
        company=company,
        service=service,
        type=type,
        title=title or "",
        description=description or "",
        created_by=user if user and user.is_authenticated else None,
    )