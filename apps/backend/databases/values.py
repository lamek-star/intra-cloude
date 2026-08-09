"""
Validates and converts a JSON-native value (as received in a row
insert/update request body) against a column's `DBColumn.DataType` —
the data-explorer counterpart to `imports/services.py`'s `_convert_value`,
which does the same job starting from raw CSV strings instead. Different
input shapes (JSON already has native int/bool/dict; CSV is always text),
so not fully shared, but both draw date/datetime/boolean rules from
`databases/formats.py` to avoid drifting apart on what's valid.
"""

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from psycopg.types.json import Jsonb

from .formats import BOOLEAN_FALSE_VALUES, BOOLEAN_TRUE_VALUES, DATE_FORMAT, DATETIME_FORMATS
from .models import DBColumn


class RowValueError(ValueError):
    pass


def validate_and_convert(value, data_type: str):
    """Returns a value safe to pass as a query parameter to psycopg for
    this column's type, or raises RowValueError."""
    if value is None:
        return None

    if data_type in (DBColumn.DataType.INTEGER, DBColumn.DataType.BIGINT):
        if isinstance(value, bool) or not isinstance(value, int):
            raise RowValueError(f"expected an integer, got {value!r}")
        return value

    if data_type == DBColumn.DataType.DECIMAL:
        if isinstance(value, bool):
            raise RowValueError(f"expected a decimal, got {value!r}")
        try:
            return Decimal(str(value))
        except InvalidOperation as exc:
            raise RowValueError(f"expected a decimal, got {value!r}") from exc

    if data_type == DBColumn.DataType.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in BOOLEAN_TRUE_VALUES | BOOLEAN_FALSE_VALUES:
            return value.lower() in BOOLEAN_TRUE_VALUES
        raise RowValueError(f"expected a boolean, got {value!r}")

    if data_type == DBColumn.DataType.DATE:
        if not isinstance(value, str):
            raise RowValueError(f"expected a {DATE_FORMAT!r}-formatted date string, got {value!r}")
        try:
            return datetime.strptime(value, DATE_FORMAT).date()
        except ValueError as exc:
            raise RowValueError(f"expected a {DATE_FORMAT!r}-formatted date string, got {value!r}") from exc

    if data_type == DBColumn.DataType.DATETIME:
        if not isinstance(value, str):
            raise RowValueError(f"expected an ISO datetime string, got {value!r}")
        for fmt in DATETIME_FORMATS:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise RowValueError(f"expected an ISO datetime string, got {value!r}")

    if data_type == DBColumn.DataType.UUID:
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, AttributeError, TypeError) as exc:
            raise RowValueError(f"expected a UUID string, got {value!r}") from exc

    if data_type in (DBColumn.DataType.TEXT, DBColumn.DataType.VARCHAR):
        if not isinstance(value, str):
            raise RowValueError(f"expected a string, got {value!r}")
        return value

    if data_type == DBColumn.DataType.JSON:
        # psycopg needs an explicit adapter to send a Python dict/list as
        # a jsonb parameter rather than failing to adapt it at all.
        return Jsonb(value)

    raise RowValueError(f"unsupported data type: {data_type!r}")
