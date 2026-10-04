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

# Exactly the characters JavaScript's `\s` matches (ECMAScript WhiteSpace + LineTerminator) --
# spelled out as code points, not left to each engine's own idea of "whitespace" -- plus the
# ASCII hyphen-minus. The browser and the separate spare-parts reference application apply
# `.replace(/[\s-]/g, "")`, so this must agree with them on every input, including em space,
# ideographic space and the byte order mark. Other dashes (en dash, minus sign) and all other
# punctuation are kept. Numeric code points, not literal characters, so the set is reviewable
# and no formatter or editor can silently change it. Vectors, run by the backend (Python and
# PostgreSQL) and the frontend: tests/fixtures/part-number-normalization.json.
WHITESPACE_CODE_POINTS = (
    0x0009,  # tab
    0x000A,  # line feed
    0x000B,  # vertical tab
    0x000C,  # form feed
    0x000D,  # carriage return
    0x0020,  # space
    0x00A0,  # no-break space
    0x1680,  # ogham space mark
    *range(0x2000, 0x200B),  # en quad .. hair space
    0x2028,  # line separator
    0x2029,  # paragraph separator
    0x202F,  # narrow no-break space
    0x205F,  # medium mathematical space
    0x3000,  # ideographic space
    0xFEFF,  # byte order mark (ECMAScript treats it as whitespace)
)
# The hyphen is last so it is a literal inside the bracket expression in Python `re` and in
# PostgreSQL regular expressions alike.
SEPARATORS = "".join(chr(code) for code in WHITESPACE_CODE_POINTS) + "-"
SEPARATOR_CLASS = "[" + SEPARATORS + "]"
_SEPARATOR_RE = re.compile(SEPARATOR_CLASS)


def normalize_search_key(value: str) -> str:
    return _SEPARATOR_RE.sub("", value).upper()
