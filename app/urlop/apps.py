from django.apps import AppConfig


class UrlopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.urlop'

    def ready(self):
        from . import signals

        print("App: %s - Loaded.." % self.name)
