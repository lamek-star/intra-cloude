"""
The data explorer's row-level query/mutation layer (Section 12 of the
master prompt): server-side pagination, sorting, filtering, and search
against a real tenant table via raw, safely-quoted SQL — Django's ORM
can't model these tables since their schema is only known at runtime
(Phase 4). Table/column identifiers here always come from already-
validated catalog rows (`databases/identifiers.py` validated them at
creation time), so only safe quoting is needed here, not re-validation.
"""

from django.db import connections
from psycopg import sql

from .models import DBColumn, DBTable
from .values import RowValueError, validate_and_convert

DEFAULT_LIMIT = 50
# Never retrieve millions of rows into the browser (Section 12 of the
# master prompt) — hard cap regardless of what the client asks for.
MAX_LIMIT = 500

_ORDERING_DIRECTIONS = {"ASC", "DESC"}


class RowNotFound(Exception):
    pass


def _column_names(table: DBTable) -> list[str]:
    # DBColumn's default Meta.ordering is alphabetical by name (sensible
    # for schema browsing) — but for row data, columns should appear in
    # the order the table was actually built (id first, then whatever was
    # added next), or "id,name,age,active" comes back as
    # "active,age,id,name" and confuses anyone looking at their own data.
    # Caught by a test asserting the expected column order, not by
    # inspection.
    return list(table.columns.order_by("created_at").values_list("name", flat=True))


def _text_column_names(table: DBTable) -> list[str]:
    return list(
        table.columns.filter(data_type__in=[DBColumn.DataType.TEXT, DBColumn.DataType.VARCHAR]).values_list(
            "name", flat=True
        )
    )


def _table_sql(table: DBTable) -> sql.Composable:
    return sql.SQL("{}.{}").format(
        sql.Identifier(table.tenant_database.schema_name), sql.Identifier(table.name)
    )


def _build_where(table: DBTable, *, filters: dict, search: str | None) -> tuple[sql.Composable, list]:
    column_names = set(_column_names(table))
    clauses: list[sql.Composable] = []
    params: list = []

    for col_name, raw_value in (filters or {}).items():
        if col_name not in column_names:
            raise RowValueError(f"unknown column: {col_name}")
        clauses.append(sql.SQL("{} = %s").format(sql.Identifier(col_name)))
        params.append(raw_value)

    if search:
        text_columns = _text_column_names(table)
        if text_columns:
            or_clauses = [sql.SQL("{} ILIKE %s").format(sql.Identifier(c)) for c in text_columns]
            clauses.append(sql.SQL("(") + sql.SQL(" OR ").join(or_clauses) + sql.SQL(")"))
            params.extend([f"%{search}%"] * len(text_columns))

    if not clauses:
        return sql.SQL(""), []
    return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(clauses), params


def list_rows(
    *,
    table: DBTable,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    ordering: str | None = None,
    filters: dict | None = None,
    search: str | None = None,
) -> dict:
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    column_names = _column_names(table)

    where_sql, where_params = _build_where(table, filters=filters or {}, search=search)

    order_sql: sql.Composable
    if ordering:
        col = ordering.lstrip("-")
        if col not in column_names:
            raise RowValueError(f"unknown column: {col}")
        direction = "DESC" if ordering.startswith("-") else "ASC"
        order_sql = sql.SQL(" ORDER BY {} {}").format(sql.Identifier(col), sql.SQL(direction))
    else:
        order_sql = sql.SQL(" ORDER BY {}").format(sql.Identifier("id"))

    select_cols = sql.SQL(", ").join(sql.Identifier(c) for c in column_names)
    query = (
        sql.SQL("SELECT {} FROM {}").format(select_cols, _table_sql(table))
        + where_sql
        + order_sql
        + sql.SQL(" LIMIT %s OFFSET %s")
    )
    count_query = sql.SQL("SELECT COUNT(*) FROM {}").format(_table_sql(table)) + where_sql

    with connections["tenant"].cursor() as cursor:
        cursor.execute(count_query, where_params)
        total = cursor.fetchone()[0]

        cursor.execute(query, [*where_params, limit, offset])
        rows = cursor.fetchall()
        result_columns = [d[0] for d in cursor.description]

    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "results": [dict(zip(result_columns, row, strict=True)) for row in rows],
    }


def get_row(table: DBTable, row_id) -> dict:
    column_names = _column_names(table)
    query = sql.SQL("SELECT {} FROM {} WHERE {} = %s").format(
        sql.SQL(", ").join(sql.Identifier(c) for c in column_names), _table_sql(table), sql.Identifier("id")
    )
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, [row_id])
        row = cursor.fetchone()
        if row is None:
            raise RowNotFound(str(row_id))
        result_columns = [d[0] for d in cursor.description]
    return dict(zip(result_columns, row, strict=True))


def insert_row(table: DBTable, data: dict) -> dict:
    columns_by_name = {c.name: c for c in table.columns.all()}
    insert_columns = []
    values = []
    for name, raw_value in data.items():
        column = columns_by_name.get(name)
        if column is None:
            raise RowValueError(f"unknown column: {name}")
        if column.is_primary_key:
            raise RowValueError(f"{name!r} is generated automatically and can't be set")
        insert_columns.append(name)
        values.append(validate_and_convert(raw_value, column.data_type))

    for column in columns_by_name.values():
        if not column.is_primary_key and not column.is_nullable and column.name not in insert_columns:
            raise RowValueError(f"{column.name!r} is required")

    column_names = _column_names(table)
    if insert_columns:
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}").format(
            _table_sql(table),
            sql.SQL(", ").join(sql.Identifier(c) for c in insert_columns),
            sql.SQL(", ").join(sql.Placeholder() for _ in insert_columns),
            sql.SQL(", ").join(sql.Identifier(c) for c in column_names),
        )
    else:
        query = sql.SQL("INSERT INTO {} DEFAULT VALUES RETURNING {}").format(
            _table_sql(table), sql.SQL(", ").join(sql.Identifier(c) for c in column_names)
        )

    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, values)
        row = cursor.fetchone()
        result_columns = [d[0] for d in cursor.description]
    return dict(zip(result_columns, row, strict=True))


def update_row(table: DBTable, row_id, data: dict) -> dict:
    if not data:
        raise RowValueError("no fields to update")

    columns_by_name = {c.name: c for c in table.columns.all()}
    set_columns = []
    values = []
    for name, raw_value in data.items():
        column = columns_by_name.get(name)
        if column is None:
            raise RowValueError(f"unknown column: {name}")
        if column.is_primary_key:
            raise RowValueError(f"{name!r} cannot be modified")
        set_columns.append(name)
        values.append(validate_and_convert(raw_value, column.data_type))

    column_names = _column_names(table)
    query = sql.SQL("UPDATE {} SET {} WHERE {} = %s RETURNING {}").format(
        _table_sql(table),
        sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in set_columns),
        sql.Identifier("id"),
        sql.SQL(", ").join(sql.Identifier(c) for c in column_names),
    )
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, [*values, row_id])
        row = cursor.fetchone()
        if row is None:
            raise RowNotFound(str(row_id))
        result_columns = [d[0] for d in cursor.description]
    return dict(zip(result_columns, row, strict=True))


def delete_row(table: DBTable, row_id) -> None:
    query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(_table_sql(table), sql.Identifier("id"))
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, [row_id])
        if cursor.rowcount == 0:
            raise RowNotFound(str(row_id))


def iter_export_rows(table: DBTable, *, batch_size: int = 1000):
    """Yields (header_row, then data rows) as lists of strings, streamed in
    batches — never materializes the whole table in memory even for a
    large export (same discipline as the CSV import pipeline)."""
    column_names = _column_names(table)
    yield column_names

    query = sql.SQL("SELECT {} FROM {} ORDER BY {}").format(
        sql.SQL(", ").join(sql.Identifier(c) for c in column_names),
        _table_sql(table),
        sql.Identifier("id"),
    )
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query)
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            for row in batch:
                yield ["" if v is None else str(v) for v in row]
