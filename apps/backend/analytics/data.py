"""
Fetches column data for analysis directly from the tenant Postgres
connection — safely quoted the same way `databases/rows.py` already
does (`psycopg.sql.Identifier` for identifiers, never string
interpolation), and always row-capped before a single byte reaches
Python/numpy/scipy (Section 20 of the master prompt: a statistics
engine must not become a denial-of-service vector).
"""

from django.conf import settings
from django.db import connections
from psycopg import sql

from databases.models import DBColumn, DBTable

NUMERIC_TYPES = {DBColumn.DataType.INTEGER, DBColumn.DataType.BIGINT, DBColumn.DataType.DECIMAL}
CATEGORICAL_TYPES = {DBColumn.DataType.TEXT, DBColumn.DataType.VARCHAR, DBColumn.DataType.BOOLEAN}
TEMPORAL_TYPES = {DBColumn.DataType.DATE, DBColumn.DataType.DATETIME}


class AnalyticsValidationError(Exception):
    pass


def _table_sql(table: DBTable) -> sql.Composable:
    return sql.SQL("{}.{}").format(
        sql.Identifier(table.tenant_database.schema_name), sql.Identifier(table.name)
    )


def get_column(table: DBTable, name: str) -> DBColumn:
    try:
        return table.columns.get(name=name)
    except DBColumn.DoesNotExist as exc:
        raise AnalyticsValidationError(f"unknown column: {name!r}") from exc


def require_types(column: DBColumn, allowed: set) -> None:
    if column.data_type not in allowed:
        raise AnalyticsValidationError(
            f"column {column.name!r} has type {column.data_type!r}, which this operation doesn't support"
        )


def fetch_columns(table: DBTable, column_names: list[str], *, row_cap: int | None = None) -> dict:
    """Returns {"rows": [(v1, v2, ...), ...], "total_rows": N, "truncated": bool}.
    `total_rows` is the table's real row count (a cheap COUNT(*)), so a
    caller can tell "truncated" apart from "the table is just small" —
    row_cap only bounds how many rows are pulled into Python, never
    silently changes what a result *means* without saying so."""
    cap = row_cap or settings.ANALYTICS_MAX_ROWS
    columns_sql = sql.SQL(", ").join(sql.Identifier(c) for c in column_names)
    query = sql.SQL("SELECT {} FROM {} LIMIT %s").format(columns_sql, _table_sql(table))
    count_query = sql.SQL("SELECT COUNT(*) FROM {}").format(_table_sql(table))

    with connections["tenant"].cursor() as cursor:
        cursor.execute(count_query)
        total_rows = cursor.fetchone()[0]

        cursor.execute(query, [cap])
        rows = cursor.fetchall()

    return {"rows": rows, "total_rows": total_rows, "truncated": total_rows > cap}
