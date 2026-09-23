from django.apps import AppConfig


class SerwisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.serwis'

    def ready(self):
        print("App: %s - Loaded.." % self.name)
        from . import signals  # noqa