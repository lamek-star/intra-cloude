from django.apps import AppConfig


class SitesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sites"
    # Not "sites": that label belongs to django.contrib.sites.
    label = "hosted_sites"
    verbose_name = "Hosted sites"
