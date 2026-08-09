"""
CSV inspection for the import preview step (Section 11 of the master
prompt: Upload -> Inspect -> Detect encoding/delimiter -> Parse headers ->
Sample rows -> Infer candidate types -> Present preview). Operates on a
bounded sample only — never reads a whole (potentially multi-gigabyte)
file for a preview.
"""

import csv
import io
from datetime import datetime

from databases.models import DBColumn

from .formats import BOOLEAN_VALUES, DATE_FORMAT, DATETIME_FORMATS

SAMPLE_BYTES = 65536
SAMPLE_ROWS = 50

# Tried in order; the last one (latin-1) never raises UnicodeDecodeError,
# so it's a guaranteed-safe last resort rather than a guess.
_ENCODINGS_TO_TRY = ("utf-8-sig", "utf-8", "latin-1")


class InspectionError(ValueError):
    pass


def detect_encoding(sample_bytes: bytes) -> str:
    for encoding in _ENCODINGS_TO_TRY:
        try:
            sample_bytes.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_delimiter(sample_text: str) -> str:
    try:
        return csv.Sniffer().sniff(sample_text, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _looks_like_date(value: str) -> bool:
    try:
        datetime.strptime(value, DATE_FORMAT)
        return True
    except ValueError:
        return False


def _looks_like_datetime(value: str) -> bool:
    return any(_matches_format(value, fmt) for fmt in DATETIME_FORMATS)


def _matches_format(value: str, fmt: str) -> bool:
    try:
        datetime.strptime(value, fmt)
        return True
    except ValueError:
        return False


def infer_type(values: list[str]) -> str:
    """Heuristic candidate type from a sample of raw string values — the
    user confirms or overrides this before anything is actually imported
    (Section 11: never silently apply an inferred type)."""
    non_empty = [v.strip() for v in values if v.strip() != ""]
    if not non_empty:
        return DBColumn.DataType.TEXT
    if all(v.lower() in BOOLEAN_VALUES for v in non_empty):
        return DBColumn.DataType.BOOLEAN
    if all(v.lstrip("-").isdigit() for v in non_empty):
        return DBColumn.DataType.INTEGER
    if all(_is_decimal(v) for v in non_empty):
        return DBColumn.DataType.DECIMAL
    if all(_looks_like_date(v) for v in non_empty):
        return DBColumn.DataType.DATE
    if all(_looks_like_datetime(v) for v in non_empty):
        return DBColumn.DataType.DATETIME
    return DBColumn.DataType.TEXT


def _is_decimal(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return "." in value or "e" in value.lower()


def inspect_sample(head: bytes) -> dict:
    """`head` is up to SAMPLE_BYTES of the raw file content. Returns
    detected encoding/delimiter, headers, a sample of parsed rows, and a
    per-column inferred candidate type."""
    encoding = detect_encoding(head)
    sample_text = head.decode(encoding, errors="replace")

    delimiter = detect_delimiter(sample_text)
    rows = list(csv.reader(io.StringIO(sample_text), delimiter=delimiter))
    # The sample may cut a final row in half — drop it rather than risk
    # inferring a type from truncated data.
    if len(head) >= SAMPLE_BYTES and rows:
        rows = rows[:-1]

    if not rows:
        raise InspectionError("CSV file appears to be empty or unreadable")

    headers = rows[0]
    sample_rows = rows[1 : SAMPLE_ROWS + 1]

    columns = []
    for i, header in enumerate(headers):
        values = [row[i] for row in sample_rows if i < len(row)]
        columns.append({"csv_column": header, "inferred_type": infer_type(values)})

    return {
        "encoding": encoding,
        "delimiter": delimiter,
        "headers": headers,
        "sample_rows": sample_rows,
        "columns": columns,
    }
