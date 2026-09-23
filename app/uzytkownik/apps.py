from django.apps import AppConfig


class UzytkownikConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.uzytkownik'

    def ready(self):
        print("App: %s - Loaded.." % self.name)
        from app.uzytkownik import signals  # noqa: F401
