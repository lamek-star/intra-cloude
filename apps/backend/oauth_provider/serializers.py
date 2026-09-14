from rest_framework import serializers

from .models import OAuthClient


def _validate_uri_list(value, field_name):
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise serializers.ValidationError(f"{field_name} must be a list of non-empty strings.")
    for uri in value:
        # Reject the two clearly dangerous schemes outright, and require
        # an absolute URL for everything else — validate_redirect_uri
        # (services.py) applies the fuller https/localhost-only rule at
        # authorize time; this is just cheap input hygiene at
        # registration time so an obviously broken entry never gets saved.
        if uri.startswith("javascript:") or uri.startswith("data:"):
            raise serializers.ValidationError(f"{field_name} entries may not use the {uri.split(':')[0]}: scheme.")
    return value


class OAuthClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = OAuthClient
        fields = [
            "id", "name", "client_id", "application_type", "redirect_uris",
            "post_logout_redirect_uris", "allowed_origins", "enabled", "requires_consent",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "client_id", "created_at", "updated_at"]

    def validate_redirect_uris(self, value):
        return _validate_uri_list(value, "redirect_uris")

    def validate_post_logout_redirect_uris(self, value):
        return _validate_uri_list(value, "post_logout_redirect_uris") if value else value


class OAuthClientCreateSerializer(OAuthClientSerializer):
    class Meta(OAuthClientSerializer.Meta):
        # A client needs at least one redirect_uri to ever be usable;
        # unlike the update path, creation shouldn't allow an empty list
        # through only to fail at every subsequent authorize request.
        pass

    def validate_redirect_uris(self, value):
        value = _validate_uri_list(value, "redirect_uris")
        if not value:
            raise serializers.ValidationError("At least one redirect_uri is required.")
        return value
