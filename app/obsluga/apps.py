from django.apps import AppConfig


class ObslugaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.obsluga'

    def ready(self):
        print("App: %s - Loaded.." % self.name)