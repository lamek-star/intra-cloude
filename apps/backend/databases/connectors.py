"""
Shared external-database connector interface (ADR-0009): connection
testing and read-only schema/data access for a `ConnectedDatabase`, kept
entirely separate from the TenantDatabase DDL/DML code path
(databases/ddl.py, databases/rows.py) since a connected-mode source is
never treated as platform-native storage — nothing here ever writes to
the external database.

PostgreSQL is the only connector implemented so far (ADR-0009 Final
Recommendation: PostgreSQL first, connected-mode read operations before
write pass-through or import-mode copying). Future engines (MySQL/
MariaDB/SQL Server/SQLite — Section 15 of the master prompt) implement
the same three operations against their own driver.
"""

from dataclasses import dataclass

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

# Kept short deliberately: a hung connection attempt to an unreachable or
# misconfigured host must not tie up a request/worker indefinitely.
CONNECT_TIMEOUT_SECONDS = 5

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


class ConnectionFailed(Exception):
    """Raised with a message safe to show a client — never the raw driver
    exception, which can embed host/credential detail in its text
    (docs/security/THREAT_MODEL.md TB6: 'errors from external DB drivers
    sanitized before returning to the client')."""


@dataclass(frozen=True)
class ConnectionParams:
    host: str
    port: int
    database: str
    username: str
    password: str
    sslmode: str


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool


@dataclass(frozen=True)
class TableInfo:
    name: str
    columns: list[ColumnInfo]


def _connect(params: ConnectionParams) -> psycopg.Connection:
    try:
        return psycopg.connect(
            host=params.host,
            port=params.port,
            dbname=params.database,
            user=params.username,
            password=params.password,
            sslmode=params.sslmode,
            connect_timeout=CONNECT_TIMEOUT_SECONDS,
            autocommit=True,
        )
    except psycopg.OperationalError as exc:
        raise ConnectionFailed("could not connect to the external database") from exc


class PostgresConnector:
    def test_connection(self, params: ConnectionParams) -> None:
        try:
            with _connect(params) as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
        except psycopg.Error as exc:
            raise ConnectionFailed("could not connect to the external database") from exc

    def introspect_schema(self, params: ConnectionParams) -> list[TableInfo]:
        try:
            with _connect(params) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                    """
                )
                rows = cur.fetchall()
        except psycopg.Error as exc:
            raise ConnectionFailed("could not read schema from the external database") from exc

        tables: dict[str, list[ColumnInfo]] = {}
        for table_name, column_name, data_type, is_nullable in rows:
            tables.setdefault(table_name, []).append(
                ColumnInfo(name=column_name, data_type=data_type, is_nullable=is_nullable == "YES")
            )
        return [TableInfo(name=name, columns=cols) for name, cols in tables.items()]

    def list_rows(
        self, params: ConnectionParams, table_name: str, *, limit: int = DEFAULT_LIMIT, offset: int = 0
    ) -> dict:
        limit = max(1, min(limit, MAX_LIMIT))
        offset = max(0, offset)
        # table_name is cross-checked by the caller (databases/connections.py)
        # against a fresh introspect_schema() result before this is ever
        # called, never taken raw from the request — but sql.Identifier is
        # used regardless, so correct quoting never depends on that being
        # true (same two-layer discipline as databases/ddl.py).
        query = sql.SQL("SELECT * FROM {} LIMIT %s OFFSET %s").format(sql.Identifier(table_name))
        count_query = sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name))
        try:
            with _connect(params) as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute(count_query)
                total_row = cur.fetchone()
                total = total_row["count"] if total_row else 0

                cur.execute(query, [limit, offset])
                rows = cur.fetchall()
        except psycopg.Error as exc:
            raise ConnectionFailed("could not read rows from the external database") from exc

        return {"count": total, "limit": limit, "offset": offset, "results": rows}


CONNECTORS = {"postgresql": PostgresConnector()}
