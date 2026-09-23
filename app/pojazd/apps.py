from django.apps import AppConfig


class PojazdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.pojazd'

    def ready(self):
        print("App: %s - Loaded.." % self.name)