from rest_framework import serializers

from .models import Application, ApplicationCredential


class ApplicationSerializer(serializers.ModelSerializer):
    # Requests counted today against daily_request_limit (applications/quotas.py).
    requests_today = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id", "organization", "name", "description", "owner", "created_at",
            "daily_request_limit", "requests_today",
        ]
        read_only_fields = fields

    def get_requests_today(self, obj) -> int:
        from .quotas import used_today

        return used_today(obj.id)


class ApplicationLimitSerializer(serializers.Serializer):
    """PATCH applications/<id>/: a whole number of requests per day, or null for no limit."""

    daily_request_limit = serializers.IntegerField(min_value=1, max_value=10_000_000, allow_null=True)


class ApplicationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")


class ApplicationCredentialSerializer(serializers.ModelSerializer):
    """Metadata only — the plaintext secret is never included here; it's
    returned exactly once, directly in the create/rotate response."""

    class Meta:
        model = ApplicationCredential
        fields = ["id", "created_at", "last_used_at", "expires_at", "revoked_at"]
        read_only_fields = fields


class ResourceGrantCreateSerializer(serializers.Serializer):
    permission_code = serializers.CharField(max_length=100)
    resource_type = serializers.CharField(max_length=100)
    resource_id = serializers.CharField(max_length=64)
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)


class ResourceGrantSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    permission = serializers.CharField(source="permission_id")
    resource_type = serializers.CharField()
    resource_id = serializers.CharField()
    granted_by = serializers.UUIDField(source="granted_by_id", allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
