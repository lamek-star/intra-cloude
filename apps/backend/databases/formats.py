"""Shared parsing constants for turning raw text/JSON input into a
DBColumn.DataType-typed Python value — used by CSV import
(imports/inspect.py, imports/services.py) and the data explorer's row
API (databases/values.py) alike, so the two paths can't silently drift
apart on what counts as a valid date/datetime/boolean."""

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")
BOOLEAN_TRUE_VALUES = {"true", "yes", "1"}
BOOLEAN_FALSE_VALUES = {"false", "no", "0"}
BOOLEAN_VALUES = BOOLEAN_TRUE_VALUES | BOOLEAN_FALSE_VALUES
