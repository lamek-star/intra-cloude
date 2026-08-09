"""
Provisions a least-privilege PostgreSQL role for the tenant database
connection — CONNECT + CREATE on that one database, never superuser,
CREATEDB, or CREATEROLE (docs/security/THREAT_MODEL.md TB3: "the app
connects as the container's bootstrap POSTGRES_USER, which is
effectively a superuser... isolation between tenant schemas is enforced
only by the application layer, not by a second, independent
database-level privilege boundary").

Postgres's own privilege model supports exactly this: a non-superuser
role granted CREATE on a database can run CREATE SCHEMA freely within
it (databases/services.py's schema-per-organization pattern needs
nothing more) and automatically owns whatever it creates, without ever
needing broader server-wide privilege.

Deliberately opt-in, not wired into docker-compose.yml or applied
automatically: the app doesn't switch which role it connects as until
an operator explicitly changes TENANT_DB_USER/TENANT_DB_PASSWORD after
verifying the new role works for their deployment (same "add-on, not a
default-breaking change" pattern as Phase 9's external-sharing toggle
and Phase 10's internet gateway).
"""

import psycopg
from django.db import connections
from psycopg import sql

CONNECT_TIMEOUT_SECONDS = 10


class TenantRoleError(Exception):
    pass


def _tenant_db_settings() -> dict:
    # connections["tenant"].settings_dict, not settings.DATABASES —
    # the test runner substitutes the real database name with a
    # "test_"-prefixed one only on the live connection wrapper (same
    # reasoning as system/backups.py:_db_settings).
    return connections["tenant"].settings_dict


def _bootstrap_connect() -> psycopg.Connection:
    db = _tenant_db_settings()
    return psycopg.connect(
        host=db["HOST"] or "localhost",
        port=int(db["PORT"] or 5432),
        dbname="postgres",
        user=db["USER"],
        password=db["PASSWORD"],
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    )


def provision_role(role_name: str, password: str) -> None:
    """Connects as the existing bootstrap (superuser) tenant role and
    creates a new, deliberately less-privileged one. Raises
    TenantRoleError with a sanitized message on any failure — never the
    raw driver exception, which could embed the bootstrap connection's
    own credentials in its text."""
    tenant_db_name = _tenant_db_settings()["NAME"]
    try:
        with _bootstrap_connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role_name])
            if cur.fetchone():
                raise TenantRoleError(f"role {role_name!r} already exists")

            # PostgreSQL's CREATE ROLE grammar doesn't accept a bind
            # parameter in the PASSWORD clause (confirmed by actually
            # running this: "syntax error at or near $1") — the password
            # is embedded via sql.Literal, which handles quoting/escaping
            # safely, the same discipline databases/ddl.py uses for
            # column defaults, never raw string interpolation.
            cur.execute(
                sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
                    sql.Identifier(role_name), sql.Literal(password)
                )
            )
            cur.execute(
                sql.SQL("GRANT CONNECT, CREATE ON DATABASE {} TO {}").format(
                    sql.Identifier(tenant_db_name), sql.Identifier(role_name)
                )
            )
            cur.execute(
                sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(
                    sql.Identifier(tenant_db_name)
                )
            )
    except TenantRoleError:
        raise
    except psycopg.Error as exc:
        raise TenantRoleError("could not provision the tenant role") from exc
