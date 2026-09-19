"""The one rule that turns typed identifiers into a comparable search key.

A part number is typed and printed many ways -- `04465-0K290`, `044650K290`,
`04465 0K290` -- and must be findable whichever way it is entered. The rule is:
remove whitespace and hyphens, uppercase. It is defined once, here, and used by
both the Python side (`normalize_search_key`, which `catalogue_storage` calls) and the
SQL side (`SEPARATOR_CLASS`, bound as a parameter to `regexp_replace` in
`databases.rows`), so the two can never drift into incompatible algorithms.

Nothing here rewrites stored data: the original value is always preserved and
displayed; only the *comparison* is normalized.
"""

import re

# Whitespace (including a non-breaking space) and the hyphen. The hyphen is last so it is
# a literal inside the bracket expression in both Python `re` and PostgreSQL regular
# expressions.
SEPARATORS = " \t\r\n\f\v\u00a0-"
SEPARATOR_CLASS = "[" + SEPARATORS + "]"
_SEPARATOR_RE = re.compile(SEPARATOR_CLASS)


def normalize_search_key(value: str) -> str:
    return _SEPARATOR_RE.sub("", value).upper()
