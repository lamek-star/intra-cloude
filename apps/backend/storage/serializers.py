from rest_framework import serializers

from .models import Bucket, FileObject, Folder


class BucketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bucket
        fields = ["id", "project", "name", "versioning_enabled", "created_at", "created_by"]
        read_only_fields = fields


class BucketCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    versioning_enabled = serializers.BooleanField(required=False, default=False)


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["id", "bucket", "parent", "name", "created_at", "created_by"]
        read_only_fields = fields


class FolderCreateSerializer(serializers.Serializer):
    # Named parent_id, not parent — "parent" collides with DRF's own
    # internal Field.parent attribute (the containing serializer/field),
    # which mypy catches as a real type conflict, not just a style nit.
    name = serializers.CharField(max_length=255)
    parent_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class FileObjectSerializer(serializers.ModelSerializer):
    # object_key is deliberately not exposed — it's an internal storage
    # detail, not something clients should see or depend on.
    class Meta:
        model = FileObject
        fields = [
            "id",
            "bucket",
            "folder",
            "original_filename",
            "display_filename",
            "mime_type",
            "size",
            "checksum_sha256",
            "status",
            "creator",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FileUpdateSerializer(serializers.Serializer):
    display_filename = serializers.CharField(max_length=255, required=False)
    folder = serializers.UUIDField(required=False, allow_null=True)
