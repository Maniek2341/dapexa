from django.apps import AppConfig


class Oferta_PracaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.oferta_praca'

    def ready(self):
        print("App: %s - Loaded.." % self.name)