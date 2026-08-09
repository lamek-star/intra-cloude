"""
Validation-logic unit tests for databases/ddl.py. Rendering the actual SQL
text requires a live psycopg connection (for encoding/type adaptation),
so *that* is covered by the full round-trip integration test in
test_databases.py against real PostgreSQL — this file covers what can be
tested without a database: every reject path.
"""

from django.test import SimpleTestCase

from databases.ddl import DDLValidationError, column_type_sql, default_clause_sql
from databases.models import DBColumn


class ColumnTypeSqlTests(SimpleTestCase):
    def test_varchar_default_length(self):
        column_type_sql(DBColumn.DataType.VARCHAR, max_length=None, precision=None, scale=None)

    def test_varchar_rejects_zero_length(self):
        with self.assertRaises(DDLValidationError):
            column_type_sql(DBColumn.DataType.VARCHAR, max_length=0, precision=None, scale=None)

    def test_varchar_rejects_absurd_length(self):
        with self.assertRaises(DDLValidationError):
            column_type_sql(DBColumn.DataType.VARCHAR, max_length=10**9, precision=None, scale=None)

    def test_decimal_rejects_scale_greater_than_precision(self):
        with self.assertRaises(DDLValidationError):
            column_type_sql(DBColumn.DataType.DECIMAL, max_length=None, precision=4, scale=10)

    def test_unsupported_type_rejected(self):
        with self.assertRaises(DDLValidationError):
            column_type_sql("not-a-real-type", max_length=None, precision=None, scale=None)


class DefaultClauseSqlTests(SimpleTestCase):
    def test_none_default_is_allowed_for_every_type(self):
        for data_type in DBColumn.DataType.values:
            default_clause_sql(data_type, None)

    def test_boolean_default_must_be_bool(self):
        default_clause_sql(DBColumn.DataType.BOOLEAN, True)
        with self.assertRaises(DDLValidationError):
            default_clause_sql(DBColumn.DataType.BOOLEAN, "true")

    def test_uuid_default_only_supports_gen_random_uuid(self):
        default_clause_sql(DBColumn.DataType.UUID, "gen_random_uuid()")
        with self.assertRaises(DDLValidationError):
            default_clause_sql(DBColumn.DataType.UUID, "00000000-0000-0000-0000-000000000000")

    def test_datetime_default_only_supports_now(self):
        default_clause_sql(DBColumn.DataType.DATETIME, "now()")
        with self.assertRaises(DDLValidationError):
            default_clause_sql(DBColumn.DataType.DATETIME, "2026-01-01")

    def test_integer_default_rejects_non_integer(self):
        default_clause_sql(DBColumn.DataType.INTEGER, 5)
        with self.assertRaises(DDLValidationError):
            default_clause_sql(DBColumn.DataType.INTEGER, "5")
        with self.assertRaises(DDLValidationError):
            default_clause_sql(DBColumn.DataType.INTEGER, True)  # bool is an int subclass

    def test_decimal_default_rejects_non_numeric(self):
        default_clause_sql(DBColumn.DataType.DECIMAL, "12.50")
        with self.assertRaises(DDLValidationError):
            default_clause_sql(DBColumn.DataType.DECIMAL, "not-a-number")

    def test_json_default_rejects_non_serializable(self):
        default_clause_sql(DBColumn.DataType.JSON, {"a": 1})
        with self.assertRaises(DDLValidationError):
            default_clause_sql(DBColumn.DataType.JSON, {1, 2, 3})  # sets aren't JSON-serializable

    def test_date_defaults_not_supported_yet(self):
        with self.assertRaises(DDLValidationError):
            default_clause_sql(DBColumn.DataType.DATE, "2026-01-01")

    def test_text_default_embeds_injection_attempt_safely(self):
        # This must not raise — the point of psycopg.sql.Literal is that
        # arbitrary string content is safe to embed. What matters is that
        # it's rendered as an escaped literal, not concatenated — verified
        # for real in the integration test since rendering needs a live
        # connection.
        default_clause_sql(DBColumn.DataType.TEXT, "'; DROP TABLE users; --")
