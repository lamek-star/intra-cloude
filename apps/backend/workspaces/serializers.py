from rest_framework import serializers

from .models import Project, Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["id", "organization", "name", "created_at", "created_by"]
        read_only_fields = fields


class WorkspaceCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "workspace", "name", "created_at", "created_by"]
        read_only_fields = fields


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
