from django.apps import AppConfig


class UrzadzenieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.urzadzenie'

    def ready(self):
        print("App: %s - Loaded.." % self.name)