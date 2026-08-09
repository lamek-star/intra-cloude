from rest_framework import serializers

from .models import ShareGrant


class ShareGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareGrant
        fields = [
            "id",
            "organization",
            "resource_type",
            "resource_id",
            "principal_type",
            "user",
            "team",
            "level",
            "expires_at",
            "revoked_at",
            "created_by",
            "created_at",
        ]
        read_only_fields = fields


class ShareGrantCreateSerializer(serializers.Serializer):
    resource_type = serializers.CharField(max_length=100)
    resource_id = serializers.UUIDField()
    principal_type = serializers.ChoiceField(choices=ShareGrant.PrincipalType.choices)
    level = serializers.ChoiceField(choices=ShareGrant.Level.choices)
    user_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    team_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        principal_type = attrs["principal_type"]
        if principal_type == ShareGrant.PrincipalType.USER and attrs.get("user_id") is None:
            raise serializers.ValidationError("user_id is required when principal_type is 'user'")
        if principal_type == ShareGrant.PrincipalType.TEAM and attrs.get("team_id") is None:
            raise serializers.ValidationError("team_id is required when principal_type is 'team'")
        return attrs


class ExternalSharingSettingSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
