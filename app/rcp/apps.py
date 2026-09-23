from django.apps import AppConfig


class RCPConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.rcp'

    def ready(self):
        print("App: %s - Loaded.." % self.name)