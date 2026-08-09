from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "timestamp",
            "actor",
            "organization",
            "action",
            "resource_type",
            "resource_id",
            "request_id",
            "result",
            "context",
        ]
        read_only_fields = fields
