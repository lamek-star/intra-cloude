from django.apps import AppConfig


class OauthProviderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "oauth_provider"
    verbose_name = "OAuth / OIDC Provider"
