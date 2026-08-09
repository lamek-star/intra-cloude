"""
Strict identifier validation — layer 1 of the two-layer defense Section 5
of the master prompt requires for anything that dynamically creates
schemas/tables ("1. strict identifier validation, 2. safe identifier
quoting"). Every schema/table/column name that ends up in dynamically
constructed DDL is validated here *before* being passed to
`psycopg.sql.Identifier` for quoting (layer 2, in databases/ddl.py)  —
quoting alone is not trusted as the only defense.
"""

import re

# Lowercase snake_case, must start with a letter, <=63 bytes (Postgres's
# identifier length limit). Deliberately does not allow the characters
# that would be needed for any SQL injection attempt (quotes, semicolons,
# whitespace, comment markers) regardless of how the value is later quoted.
#
# \Z, not the bare $ — Python's `$` matches just before a trailing "\n" as
# well as at the true end of string, so "customers\n" would otherwise slip
# past this validator (caught by actually testing a newline-suffixed
# injection attempt, not by inspection).
_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}\Z")

# Reserved so a user-chosen table/column name can never collide with the
# platform-managed primary key column every table gets.
RESERVED_COLUMN_NAMES = {"id"}


class IdentifierError(ValueError):
    pass


def validate_identifier(name: str, *, kind: str = "identifier") -> str:
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise IdentifierError(
            f"Invalid {kind} {name!r}: must start with a lowercase letter and contain only "
            "lowercase letters, digits, and underscores, up to 63 characters."
        )
    return name


def validate_column_name(name: str) -> str:
    validate_identifier(name, kind="column name")
    if name in RESERVED_COLUMN_NAMES:
        raise IdentifierError(f"Column name {name!r} is reserved.")
    return name
