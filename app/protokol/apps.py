from django.apps import AppConfig


class ProtokolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.protokol'

    def ready(self):
        print("App: %s - Loaded.." % self.name)
