from rest_framework import serializers

from .models import Dashboard


class AnalysisRequestSerializer(serializers.Serializer):
    operation = serializers.CharField()
    params = serializers.JSONField(required=False, default=dict)


class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ["id", "tenant_database", "name", "widgets", "created_by", "created_at", "updated_at"]
        read_only_fields = fields


class DashboardCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    widgets = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class DashboardUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    widgets = serializers.ListField(child=serializers.DictField(), required=False)
