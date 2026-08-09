from rest_framework import serializers

from .models import ConnectedDatabase, DBColumn, DBForeignKey, DBTable, TenantDatabase


class TenantDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantDatabase
        fields = ["id", "project", "name", "created_at", "created_by"]
        read_only_fields = fields


class TenantDatabaseCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)


class ForeignKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = DBForeignKey
        fields = ["id", "column", "references_table", "references_column", "on_delete", "created_at"]
        read_only_fields = fields


class ColumnSerializer(serializers.ModelSerializer):
    foreign_key = ForeignKeySerializer(read_only=True)

    class Meta:
        model = DBColumn
        fields = [
            "id",
            "table",
            "name",
            "data_type",
            "max_length",
            "precision",
            "scale",
            "is_primary_key",
            "is_nullable",
            "is_unique",
            "default_value",
            "created_at",
            "foreign_key",
        ]
        read_only_fields = fields


class TableSerializer(serializers.ModelSerializer):
    columns = ColumnSerializer(many=True, read_only=True)

    class Meta:
        model = DBTable
        fields = ["id", "tenant_database", "name", "created_at", "created_by", "columns"]
        read_only_fields = fields


class TableCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=63)


class ColumnCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=63)
    data_type = serializers.ChoiceField(choices=DBColumn.DataType.choices)
    max_length = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=1)
    precision = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=1)
    scale = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=0)
    is_nullable = serializers.BooleanField(required=False, default=True)
    is_unique = serializers.BooleanField(required=False, default=False)
    default_value = serializers.JSONField(required=False, allow_null=True, default=None)


class ForeignKeyCreateSerializer(serializers.Serializer):
    column_id = serializers.UUIDField()
    references_table_id = serializers.UUIDField()
    references_column_id = serializers.UUIDField()
    on_delete = serializers.ChoiceField(
        choices=DBForeignKey.OnDelete.choices, required=False, default=DBForeignKey.OnDelete.RESTRICT
    )


class ConnectedDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectedDatabase
        # Never the password or its encrypted form — this is the only
        # serializer connected-database views ever return.
        fields = [
            "id",
            "project",
            "name",
            "engine",
            "host",
            "port",
            "database_name",
            "username",
            "sslmode",
            "status",
            "last_tested_at",
            "last_test_error",
            "created_at",
            "created_by",
        ]
        read_only_fields = fields


class ConnectedDatabaseCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    engine = serializers.ChoiceField(
        choices=ConnectedDatabase.Engine.choices, default=ConnectedDatabase.Engine.POSTGRESQL
    )
    host = serializers.CharField(max_length=255)
    port = serializers.IntegerField(min_value=1, max_value=65535, default=5432)
    database_name = serializers.CharField(max_length=200)
    username = serializers.CharField(max_length=200)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    sslmode = serializers.ChoiceField(
        choices=ConnectedDatabase.SSLMode.choices, default=ConnectedDatabase.SSLMode.REQUIRE
    )
