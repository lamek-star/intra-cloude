from rest_framework import serializers

from .models import ExportJob, RestoreJob


class ExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportJob
        fields = [
            "id",
            "organization",
            "status",
            "encrypted",
            "size_bytes",
            "checksum_sha256",
            "error_message",
            "created_by",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields


class ExportJobCreateSerializer(serializers.Serializer):
    # write_only + never echoed back anywhere — same discipline as
    # ConnectedDatabaseCreateSerializer's password field.
    passphrase = serializers.CharField(
        required=False, allow_null=True, write_only=True, trim_whitespace=False, min_length=8
    )


class RestoreJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestoreJob
        fields = [
            "id",
            "organization",
            "status",
            "report",
            "error_message",
            "created_by",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields
