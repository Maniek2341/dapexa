from django.apps import AppConfig


class ZadanieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.zadanie'

    def ready(self):
        print("App: %s - Loaded.." % self.name)