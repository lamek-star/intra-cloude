from rest_framework import serializers

from .models import Environment, EnvironmentSecret, EnvironmentVariable, EnvironmentWebhook


class EnvironmentSerializer(serializers.ModelSerializer):
    database_status = serializers.SerializerMethodField()
    storage_status = serializers.SerializerMethodField()
    credential_count = serializers.SerializerMethodField()

    class Meta:
        model = Environment
        fields = [
            "id",
            "application",
            "name",
            "slug",
            "environment_type",
            "is_production_tier",
            "status",
            "config",
            "created_by",
            "created_at",
            "updated_at",
            "last_activity_at",
            "database_status",
            "storage_status",
            "credential_count",
        ]
        read_only_fields = fields

    def get_database_status(self, obj) -> str:
        return "connected" if getattr(obj, "tenant_database", None) else "not_connected"

    def get_storage_status(self, obj) -> str:
        return "connected" if getattr(obj, "bucket", None) else "not_connected"

    def get_credential_count(self, obj) -> int:
        return obj.credentials.filter(revoked_at__isnull=True).count()


class EnvironmentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    environment_type = serializers.CharField(max_length=30, default="development")
    is_production_tier = serializers.BooleanField(required=False, allow_null=True, default=None)
    config = serializers.JSONField(required=False, default=dict)


class EnvironmentUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    environment_type = serializers.CharField(max_length=30, required=False)
    is_production_tier = serializers.BooleanField(required=False)
    config = serializers.JSONField(required=False)


class EnvironmentCloneSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class EnvironmentDeleteSerializer(serializers.Serializer):
    confirm_name = serializers.CharField(max_length=100)
    confirm_production_understanding = serializers.BooleanField(required=False, default=False)


class EnvironmentVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentVariable
        fields = ["id", "key", "value", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EnvironmentVariableWriteSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=200)
    value = serializers.CharField(allow_blank=True)


class EnvironmentSecretSerializer(serializers.ModelSerializer):
    """Metadata only -- value_ciphertext is never serialized, and there
    is no field here that could ever carry a decrypted value. The
    plaintext is returned exactly once, directly in the create/rotate
    view response, never through this serializer."""

    class Meta:
        model = EnvironmentSecret
        fields = ["id", "key", "created_at", "rotated_at"]
        read_only_fields = fields


class EnvironmentSecretWriteSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=200)
    value = serializers.CharField()


class EnvironmentWebhookSerializer(serializers.ModelSerializer):
    """signing_secret_ciphertext is never serialized -- same discipline
    as EnvironmentSecretSerializer."""

    class Meta:
        model = EnvironmentWebhook
        fields = ["id", "url", "event_types", "enabled", "created_at"]
        read_only_fields = ["id", "created_at"]


class EnvironmentWebhookCreateSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=500)
    event_types = serializers.ListField(child=serializers.CharField(max_length=100), default=list)
    enabled = serializers.BooleanField(default=True)


class EnvironmentWebhookUpdateSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=500, required=False)
    event_types = serializers.ListField(child=serializers.CharField(max_length=100), required=False)
    enabled = serializers.BooleanField(required=False)


class DatabaseBindingSerializer(serializers.Serializer):
    tenant_database_id = serializers.UUIDField(allow_null=True)


class StorageBindingSerializer(serializers.Serializer):
    bucket_id = serializers.UUIDField(allow_null=True)


class EnvironmentCredentialIssueSerializer(serializers.Serializer):
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
