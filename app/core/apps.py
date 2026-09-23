from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.core'

    def ready(self):
        print("App: %s - Loaded.." % self.name)
        import app.core.signals
        from app.core.subscription_limits import register_subscription_limit_signals

        register_subscription_limit_signals()

        
