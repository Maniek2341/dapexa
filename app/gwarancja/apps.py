from django.apps import AppConfig


class GwarancjaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.gwarancja'

    def ready(self):
        print("App: %s - Loaded.." % self.name)