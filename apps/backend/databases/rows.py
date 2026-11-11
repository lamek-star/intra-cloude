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
from .normalization import SEPARATOR_CLASS, normalize_search_key
from .values import RowValueError, validate_and_convert

DEFAULT_LIMIT = 50
# Never retrieve millions of rows into the browser (Section 12 of the
# master prompt) — hard cap regardless of what the client asks for.
MAX_LIMIT = 500

_ORDERING_DIRECTIONS = {"ASC", "DESC"}


class RowNotFound(Exception):
    pass


class RowConflict(Exception):
    """The row exists but no longer matches the caller's expected
    values -- a genuine concurrent change, not a missing row. Distinct
    from RowNotFound so a caller can return 409 (conflict) rather than
    404 (missing)."""


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


def _like_escape(value: str) -> str:
    """Make `%`, `_` and the escape character literal in a LIKE/ILIKE pattern."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _build_where(
    table: DBTable, *, filters: dict, search: str | None, normalized_search: bool = False
) -> tuple[sql.Composable, list]:
    column_names = set(_column_names(table))
    clauses: list[sql.Composable] = []
    params: list = []

    for col_name, raw_value in (filters or {}).items():
        if col_name not in column_names:
            raise RowValueError(f"unknown column: {col_name}")
        if isinstance(raw_value, (list, tuple, set)):
            # Internal/programmatic filtering only (e.g. app_platform's
            # unit-scoped record access, restricting a column to a set of
            # allowed values) -- the HTTP row API never sends a list here,
            # only a single raw query-string value per filter key. An
            # empty set can never match any row; build that explicitly
            # rather than emitting invalid `IN ()` SQL.
            values = list(raw_value)
            if not values:
                clauses.append(sql.SQL("1 = 0"))
                continue
            placeholders = sql.SQL(", ").join(sql.SQL("%s") for _ in values)
            clauses.append(sql.SQL("{} IN ({})").format(sql.Identifier(col_name), placeholders))
            params.extend(values)
        else:
            clauses.append(sql.SQL("{} = %s").format(sql.Identifier(col_name)))
            params.append(raw_value)

    if search:
        text_columns = _text_column_names(table)
        if text_columns:
            or_clauses = [sql.SQL("{} ILIKE %s ESCAPE '\\'").format(sql.Identifier(c)) for c in text_columns]
            params.extend([f"%{_like_escape(search)}%"] * len(text_columns))
            # Opt-in: also match with whitespace/hyphens removed and case folded on both
            # sides, so `044650K290` finds `04465-0K290` (databases/normalization.py). A
            # query made only of separators has no key and adds no clause -- otherwise
            # it would match every row.
            key = normalize_search_key(search) if normalized_search else ""
            if key:
                pattern = f"%{_like_escape(key)}%"
                for column in text_columns:
                    or_clauses.append(
                        sql.SQL("upper(regexp_replace({}, %s, '', 'g')) LIKE %s ESCAPE '\\'").format(
                            sql.Identifier(column)
                        )
                    )
                    params.extend([SEPARATOR_CLASS, pattern])
            clauses.append(sql.SQL("(") + sql.SQL(" OR ").join(or_clauses) + sql.SQL(")"))

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
    normalized_search: bool = False,
) -> dict:
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    column_names = _column_names(table)

    where_sql, where_params = _build_where(
        table, filters=filters or {}, search=search, normalized_search=normalized_search
    )

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


def update_row_if(table: DBTable, row_id, *, expected: dict, data: dict) -> dict:
    """Like update_row, but the UPDATE's WHERE clause also requires each
    `expected` column to still hold its given value -- a compare-and-swap,
    not a read-then-write. This is the concurrency-safety primitive App
    Platform's workflow engine uses to apply a state transition: only one
    of two racing, mutually-exclusive transitions starting from the same
    recorded state can ever succeed, with the loser getting a clean
    RowConflict rather than a corrupted write -- a real Postgres operation
    is the gate, matching this project's existing "let it race, let the
    database be the real gate" discipline (see app_platform/records.py's
    own many-to-many update docstring) rather than an application-level
    lock. `expected` may be empty (no extra WHERE conditions at all -- a
    transition valid from any current state)."""
    if not data:
        raise RowValueError("no fields to update")

    columns_by_name = {c.name: c for c in table.columns.all()}

    def _validated(items):
        names, values = [], []
        for name, raw_value in items.items():
            column = columns_by_name.get(name)
            if column is None:
                raise RowValueError(f"unknown column: {name}")
            if column.is_primary_key:
                raise RowValueError(f"{name!r} cannot be modified")
            names.append(name)
            values.append(validate_and_convert(raw_value, column.data_type))
        return names, values

    set_columns, set_values = _validated(data)
    expected_columns, expected_values = _validated(expected or {})

    column_names = _column_names(table)
    where_clauses = [sql.SQL("{} = %s").format(sql.Identifier("id"))]
    where_params: list = [row_id]
    for name, value in zip(expected_columns, expected_values, strict=True):
        # SQL's three-valued logic means "= NULL" never matches anything,
        # even a genuinely NULL column -- a real bug caught by
        # databases/tests/test_row_conditional_update.py's own
        # null-expected-value test, not by inspection.
        if value is None:
            where_clauses.append(sql.SQL("{} IS NULL").format(sql.Identifier(name)))
        else:
            where_clauses.append(sql.SQL("{} = %s").format(sql.Identifier(name)))
            where_params.append(value)
    query = (
        sql.SQL("UPDATE {} SET {}").format(
            _table_sql(table),
            sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in set_columns),
        )
        + sql.SQL(" WHERE ")
        + sql.SQL(" AND ").join(where_clauses)
        + sql.SQL(" RETURNING {}").format(sql.SQL(", ").join(sql.Identifier(c) for c in column_names))
    )
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, [*set_values, *where_params])
        row = cursor.fetchone()
        if row is None:
            # Zero rows matched -- distinguish "doesn't exist" from
            # "exists but expected no longer holds" with one cheap lookup,
            # the same not-found-vs-conflict split
            # app_platform/provisioning.py's reserve() already makes for a
            # stale-fingerprint reservation attempt.
            get_row(table, row_id)  # raises RowNotFound if truly missing
            raise RowConflict(str(row_id))
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
