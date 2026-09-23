try:
    from .celery import app as celery_app
except ModuleNotFoundError as exc:  # Celery is optional in local/test environments.
    if exc.name != "celery":
        raise
    celery_app = None

__all__ = ("celery_app",)
