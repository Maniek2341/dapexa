from django.apps import AppConfig


class FakturaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.faktura'

    def ready(self):
        print("App: %s - Loaded.." % self.name)