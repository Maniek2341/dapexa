from django.apps import AppConfig


class KlientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.klient'

    def ready(self):
        print("App: %s - Loaded.." % self.name)