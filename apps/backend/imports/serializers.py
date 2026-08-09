from rest_framework import serializers

from .models import ImportJob, ImportJobError


class ColumnMappingEntrySerializer(serializers.Serializer):
    csv_column = serializers.CharField()
    target_column = serializers.CharField()
    target_type = serializers.CharField()


class ImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = [
            "id",
            "file",
            "table",
            "encoding",
            "delimiter",
            "column_mapping",
            "status",
            "total_rows",
            "imported_rows",
            "rejected_rows",
            "error_message",
            "created_by",
            "created_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = fields


class ImportJobCreateSerializer(serializers.Serializer):
    file_id = serializers.UUIDField()
    encoding = serializers.CharField(max_length=20)
    delimiter = serializers.CharField(max_length=1)
    column_mapping = ColumnMappingEntrySerializer(many=True)


class ImportJobErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJobError
        fields = ["id", "row_number", "message", "raw_row", "created_at"]
        read_only_fields = fields
