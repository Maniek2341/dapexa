from django.apps import AppConfig


class PracaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.praca'

    def ready(self):
        from . import signals  # noqa: F401

        print("App: %s - Loaded.." % self.name)
