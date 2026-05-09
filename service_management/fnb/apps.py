from django.apps import AppConfig

class FnbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fnb'

    def ready(self):
        import fnb.signals
