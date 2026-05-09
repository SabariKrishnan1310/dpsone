from django.apps import AppConfig

class SterlingCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sterling_core'

    def ready(self):
        import sterling_core.signals
