from django.apps import AppConfig


class ServiceAppsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "service_apps"
    verbose_name = "Service applications"

    def ready(self):
        from . import signals  # noqa: F401  (connects the logout handler)
