"""Database provisioning for service applications: one login role per deployment, one schema per
installed instance, in the tenant PostgreSQL database (ADR-0005, ADR-0018).

The role is least-privilege: LOGIN, CONNECT on the tenant database, ownership of its own schema --
never superuser, CREATEDB, CREATEROLE, or CREATE on the database (so it cannot create schemas of
its own). Other organizations' schemas are owned by the bootstrap role and grant it nothing.
PostgreSQL's system catalogs remain readable by every role (names of other schemas' tables, not
their rows) -- a documented limitation of schema-level isolation.

Every statement names identifiers through psycopg.sql.Identifier and passes values as parameters
or sql.Literal (CREATE ROLE's PASSWORD clause takes no bind parameter), never string formatting.
"""

import re

import psycopg
from django.db import connections
from psycopg import sql

CONNECT_TIMEOUT_SECONDS = 10
_IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class ProvisioningError(Exception):
    """Sanitized failure: never carries the driver's message, which can include connection details."""


def _settings() -> dict:
    return connections["tenant"].settings_dict


def _connect(dbname: str | None = None) -> psycopg.Connection:
    db = _settings()
    return psycopg.connect(
        host=db["HOST"] or "localhost",
        port=int(db["PORT"] or 5432),
        dbname=dbname or db["NAME"],
        user=db["USER"],
        password=db["PASSWORD"],
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    )


def _check(name: str) -> str:
    if not _IDENT.match(name):
        raise ProvisioningError(f"Invalid identifier {name!r}.")
    return name


def ensure_role(role: str, password: str) -> None:
    """Creates the deployment's login role, or resets its password to the configured one."""
    _check(role)
    if not password:
        raise ProvisioningError("The service database password is not configured.")
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role])
            verb = "ALTER" if cur.fetchone() else "CREATE"
            cur.execute(
                sql.SQL(
                    verb + " ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT "
                    "CONNECTION LIMIT 30 PASSWORD {}"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
            cur.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(_settings()["NAME"]), sql.Identifier(role)
                )
            )
    except psycopg.Error as exc:
        raise ProvisioningError("Could not create the application's database role.") from exc


def ensure_schema(schema: str, role: str) -> None:
    """Creates the instance's schema owned by the deployment role (idempotent), and hands every
    object in it back to that role -- a restore run by the bootstrap role, or a schema created
    before this role existed, must never leave the application unable to migrate its own tables."""
    _check(schema)
    _check(role)
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION {}").format(
                    sql.Identifier(schema), sql.Identifier(role)
                )
            )
            cur.execute(
                sql.SQL("ALTER SCHEMA {} OWNER TO {}").format(sql.Identifier(schema), sql.Identifier(role))
            )
            cur.execute(sql.SQL("REVOKE ALL ON SCHEMA {} FROM PUBLIC").format(sql.Identifier(schema)))
            cur.execute(
                sql.SQL("ALTER ROLE {} SET search_path TO {}").format(
                    sql.Identifier(role), sql.Identifier(schema)
                )
            )
            _repair_ownership(cur, schema, role)
    except psycopg.Error as exc:
        raise ProvisioningError("Could not create the application's database schema.") from exc


def _repair_ownership(cur, schema: str, role: str) -> None:
    # Tables, sequences, views (indexes follow their table). Identity sequences are owned by
    # their table and move with it, so they are skipped.
    cur.execute(
        """
        SELECT c.relname, c.relkind
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
           AND pg_get_userbyid(c.relowner) <> %s
           AND NOT (c.relkind = 'S' AND EXISTS (
                 SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype IN ('a', 'i')))
        """,
        [schema, role],
    )
    kinds = {
        "r": "TABLE",
        "p": "TABLE",
        "v": "VIEW",
        "m": "MATERIALIZED VIEW",
        "S": "SEQUENCE",
        "f": "FOREIGN TABLE",
    }
    for name, kind in cur.fetchall():
        cur.execute(
            sql.SQL("ALTER " + kinds[kind] + " {}.{} OWNER TO {}").format(
                sql.Identifier(schema), sql.Identifier(name), sql.Identifier(role)
            )
        )
    cur.execute(
        """
        SELECT p.oid::regprocedure::text FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = %s AND pg_get_userbyid(p.proowner) <> %s
        """,
        [schema, role],
    )
    for (signature,) in cur.fetchall():
        # regprocedure text is already a fully quoted, schema-qualified signature.
        cur.execute(sql.SQL("ALTER FUNCTION " + signature + " OWNER TO {}").format(sql.Identifier(role)))
    cur.execute(
        """
        SELECT c.collname FROM pg_collation c JOIN pg_namespace n ON n.oid = c.collnamespace
         WHERE n.nspname = %s AND pg_get_userbyid(c.collowner) <> %s
        """,
        [schema, role],
    )
    for (name,) in cur.fetchall():
        cur.execute(
            sql.SQL("ALTER COLLATION {}.{} OWNER TO {}").format(
                sql.Identifier(schema), sql.Identifier(name), sql.Identifier(role)
            )
        )


def schema_exists(schema: str) -> bool:
    _check(schema)
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", [schema])
            return cur.fetchone() is not None
    except psycopg.Error as exc:
        raise ProvisioningError("Could not reach the tenant database.") from exc


def drop_schema(schema: str) -> None:
    """Permanently removes an application's data. Only ever called after an explicit, confirmed
    removal request (services.remove with drop_data=True)."""
    _check(schema)
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
    except psycopg.Error as exc:
        raise ProvisioningError("Could not remove the application's database schema.") from exc


def schema_summary(schema: str, tables: tuple[str, ...]) -> dict:
    """Row counts of the application's main tables, for the removal preview (no row content)."""
    _check(schema)
    wanted = list(tables)
    out = {}
    try:
        with _connect() as conn, conn.cursor() as cur:
            for table in wanted:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                    [schema, table],
                )
                if cur.fetchone():
                    cur.execute(
                        sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                            sql.Identifier(schema), sql.Identifier(table)
                        )
                    )
                    row = cur.fetchone()
                    out[table] = row[0] if row else 0
    except psycopg.Error as exc:
        raise ProvisioningError("Could not read the application's database schema.") from exc
    return out
