from django.apps import AppConfig


class DostawcyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.dostawcy"
    verbose_name = "Integracje z dostawcami"

    def ready(self):
        from . import signals  # noqa: F401
