"""Shared parsing constants used by both type inference (imports/inspect.py,
heuristic, on a sample) and actual value conversion (imports/services.py,
must succeed or the row is rejected) — kept in one place so they can't
silently drift apart."""

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")
BOOLEAN_TRUE_VALUES = {"true", "yes", "1"}
BOOLEAN_FALSE_VALUES = {"false", "no", "0"}
BOOLEAN_VALUES = BOOLEAN_TRUE_VALUES | BOOLEAN_FALSE_VALUES
