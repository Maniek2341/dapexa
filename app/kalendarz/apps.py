from django.apps import AppConfig


class KalendarzConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.kalendarz'

    def ready(self):
        print("App: %s - Loaded.." % self.name)