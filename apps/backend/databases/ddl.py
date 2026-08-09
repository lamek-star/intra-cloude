"""
Safe DDL construction — layer 2 of the two-layer defense Section 5 of the
master prompt requires ("1. strict identifier validation, 2. safe
identifier quoting"). Every identifier here has already passed
databases/identifiers.py validation; this module is responsible for
quoting identifiers (`psycopg.sql.Identifier`) and safely embedding
constant values (`psycopg.sql.Literal`) — never plain string
interpolation/f-strings into SQL text.
"""

from decimal import Decimal, InvalidOperation

from psycopg import sql

from .models import DBColumn


class DDLValidationError(ValueError):
    """A column/type/default combination that fails validation before any
    SQL is constructed — always caught and reported before touching the
    database."""


_PG_TYPES: dict[str, str] = {
    DBColumn.DataType.TEXT.value: "TEXT",
    DBColumn.DataType.INTEGER.value: "INTEGER",
    DBColumn.DataType.BIGINT.value: "BIGINT",
    DBColumn.DataType.BOOLEAN.value: "BOOLEAN",
    DBColumn.DataType.DATE.value: "DATE",
    DBColumn.DataType.DATETIME.value: "TIMESTAMPTZ",
    DBColumn.DataType.UUID.value: "UUID",
    DBColumn.DataType.JSON.value: "JSONB",
}

_MAX_VARCHAR_LENGTH = 10_485_760  # Postgres's own practical ceiling
_MAX_DECIMAL_PRECISION = 1000


def column_type_sql(
    data_type: str, *, max_length: int | None, precision: int | None, scale: int | None
) -> sql.Composable:
    if data_type == DBColumn.DataType.VARCHAR:
        # `or` would treat max_length=0 as falsy and silently substitute
        # the default instead of rejecting it — caught by actually testing
        # a zero max_length, not by inspection.
        length = max_length if max_length is not None else 255
        if not (0 < length <= _MAX_VARCHAR_LENGTH):
            raise DDLValidationError(f"varchar max_length must be between 1 and {_MAX_VARCHAR_LENGTH}")
        return sql.SQL("VARCHAR({})").format(sql.Literal(length))

    if data_type == DBColumn.DataType.DECIMAL:
        p = precision if precision is not None else 18
        s = scale if scale is not None else 4
        if not (0 < p <= _MAX_DECIMAL_PRECISION) or not (0 <= s <= p):
            raise DDLValidationError("decimal precision/scale out of range (0 <= scale <= precision <= 1000)")
        return sql.SQL("NUMERIC({}, {})").format(sql.Literal(p), sql.Literal(s))

    if data_type not in _PG_TYPES:
        raise DDLValidationError(f"Unsupported data type: {data_type!r}")
    return sql.SQL(_PG_TYPES[data_type])


def default_clause_sql(data_type: str, default_value) -> sql.Composable:
    """Returns a ` DEFAULT ...` clause (with leading space) or empty SQL.
    `default_value` must already be validated against `data_type` — this
    is the "approved safe set" of defaults from Section 9 of the master
    prompt, not arbitrary unvalidated expressions."""
    if default_value is None:
        return sql.SQL("")

    if data_type == DBColumn.DataType.BOOLEAN:
        if not isinstance(default_value, bool):
            raise DDLValidationError("Boolean default must be true or false")
        return sql.SQL(" DEFAULT {}").format(sql.Literal(default_value))

    if data_type == DBColumn.DataType.UUID:
        if default_value != "gen_random_uuid()":
            raise DDLValidationError(
                "The only supported UUID default is the literal string 'gen_random_uuid()'"
            )
        return sql.SQL(" DEFAULT gen_random_uuid()")

    if data_type == DBColumn.DataType.DATETIME:
        if default_value != "now()":
            raise DDLValidationError("The only supported datetime default is the literal string 'now()'")
        return sql.SQL(" DEFAULT now()")

    if data_type in (DBColumn.DataType.TEXT, DBColumn.DataType.VARCHAR):
        if not isinstance(default_value, str):
            raise DDLValidationError("Text/varchar default must be a string")
        return sql.SQL(" DEFAULT {}").format(sql.Literal(default_value))

    if data_type in (DBColumn.DataType.INTEGER, DBColumn.DataType.BIGINT):
        if not isinstance(default_value, int) or isinstance(default_value, bool):
            raise DDLValidationError("Integer/bigint default must be an integer")
        return sql.SQL(" DEFAULT {}").format(sql.Literal(default_value))

    if data_type == DBColumn.DataType.DECIMAL:
        try:
            Decimal(str(default_value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise DDLValidationError("Decimal default must be a numeric value") from exc
        return sql.SQL(" DEFAULT {}").format(sql.Literal(str(default_value)))

    if data_type == DBColumn.DataType.JSON:
        import json as json_module

        try:
            text = json_module.dumps(default_value)
        except TypeError as exc:
            raise DDLValidationError("JSON default must be JSON-serializable") from exc
        return sql.SQL(" DEFAULT {}::jsonb").format(sql.Literal(text))

    if data_type == DBColumn.DataType.DATE:
        raise DDLValidationError("Date column defaults are not supported yet")

    raise DDLValidationError(f"Unsupported data type: {data_type!r}")
