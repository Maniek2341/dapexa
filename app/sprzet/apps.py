from django.apps import AppConfig


class SprzetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.sprzet'

    def ready(self):
        print("App: %s - Loaded.." % self.name)