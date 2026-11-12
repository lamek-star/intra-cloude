"""
Shared external-database connector interface (ADR-0009): connection
testing and read-only schema/data access for a `ConnectedDatabase`, kept
entirely separate from the TenantDatabase DDL/DML code path
(databases/ddl.py, databases/rows.py) since a connected-mode source is
never treated as platform-native storage — nothing here ever writes to
the external database.

PostgreSQL came first (ADR-0009); MySQL/MariaDB (PyMySQL) and SQL Server
(pymssql) implement the same three operations against their own driver
(ADR-0024), with the same rules: the host is checked against the SSRF
guard on every connection and the connection goes to the address that was
checked, only SELECT statements are ever sent, table names are quoted by
the driver's own identifier rules and are cross-checked by the caller
against a fresh schema read.
"""

import ipaddress
import socket
import ssl
from dataclasses import dataclass

import psycopg
from django.conf import settings
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


class UnsafeHost(ConnectionFailed):
    """Raised when a target host resolves to an address this deployment
    must never let the backend dial (Section 30 of the master prompt:
    SSRF via the connected-database feature). A subclass of
    ConnectionFailed so every existing caller's `except ConnectionFailed`
    already handles it correctly."""


# Always blocked, regardless of configuration — none of these are ever a
# legitimate connected-database target. Link-local matters most: it
# covers cloud metadata endpoints like 169.254.169.254, a classic SSRF
# pivot point that has nothing to do with this being a local-first
# product. Loopback and RFC1918 private ranges are deliberately NOT in
# this bucket — this is an on-prem, local-first product, and a
# customer's own PostgreSQL (or, in this dev/CI setup, the very tenant
# database this backend already uses) legitimately lives on the LAN or
# even on localhost. See CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS below
# for deployments where that assumption doesn't hold.
_ALWAYS_UNSAFE_ATTRS = ("is_link_local", "is_unspecified", "is_reserved", "is_multicast")

# Only blocked when CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS is enabled
# (settings.py) — a stricter posture for a hosted/multi-tenant topology
# where "private network" might mean the host's own internal Docker
# network, which tenants must not be able to reach.
_PRIVATE_NETWORK_ATTRS = ("is_private", "is_loopback")


def assert_host_is_safe(host: str) -> tuple[str, ...]:
    """Resolves `host` and rejects it if it lands on an address this
    process must never be tricked into reaching. Re-checked on every
    connection attempt (not just once at creation time) so a host that
    later resolves differently (DNS rebinding) doesn't get a free pass
    from an earlier check."""
    try:
        addr_infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeHost(f"could not resolve host {host!r}") from exc

    if not addr_infos:
        raise UnsafeHost("host has no usable addresses")
    addresses: tuple[str, ...] = tuple(dict.fromkeys(str(info[4][0]) for info in addr_infos))
    block_private = settings.CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS
    for *_rest, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        # Loopback is exempted from the always-unsafe bucket even though
        # `is_reserved` is True for it: Python's ipaddress module reports
        # IPv6 `::1` as reserved (unlike IPv4 `127.0.0.1`, where
        # is_reserved is False) — an stdlib quirk, confirmed directly
        # against CPython, not a documented IANA distinction. Left
        # unhandled, that quirk silently blocked IPv6 loopback under the
        # default (non-strict) policy, contradicting the documented intent
        # that loopback is only ever blocked via
        # CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS below — and broke real
        # CI runs where `localhost` resolves to `::1`.
        if ip.is_loopback:
            if block_private:
                raise UnsafeHost(f"{host!r} resolves to a private address ({ip}), blocked on this deployment")
            continue
        if any(getattr(ip, attr) for attr in _ALWAYS_UNSAFE_ATTRS):
            raise UnsafeHost(f"{host!r} resolves to a non-routable address ({ip}) and cannot be used")
        if block_private and any(getattr(ip, attr) for attr in _PRIVATE_NETWORK_ATTRS):
            raise UnsafeHost(f"{host!r} resolves to a private address ({ip}), blocked on this deployment")
    return addresses


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
    addresses = assert_host_is_safe(params.host)
    try:
        return psycopg.connect(
            host=params.host,
            # Bind the connection to the address we validated. Keep host for
            # TLS verify-full/SNI; never let libpq resolve it a second time.
            hostaddr=addresses[0],
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


def _jsonable(value):
    """A cell as the API can send it: binary columns as their size (never their bytes), sets as lists."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} bytes>"
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    return value


def _clean_rows(rows) -> list[dict]:
    return [{k: _jsonable(v) for k, v in row.items()} for row in rows]


# ---- MySQL / MariaDB ---------------------------------------------------------------------------------------
class _NamedTLSContext(ssl.SSLContext):
    """The connection goes to the checked IP address, but the certificate must be for the host's name: the
    driver would otherwise ask TLS to verify the IP."""

    expected_name = ""

    def wrap_socket(self, sock, *args, server_hostname=None, **kwargs):
        return super().wrap_socket(sock, *args, server_hostname=self.expected_name, **kwargs)


def _mysql_identifier(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


class MySQLConnector:
    """MySQL 5.7+/8.x and MariaDB, through PyMySQL. The session is set READ ONLY as well."""

    def _connect(self, params: ConnectionParams):
        import pymysql

        addresses = assert_host_is_safe(params.host)
        context = None
        if params.sslmode == "verify-full":
            context = _NamedTLSContext(ssl.PROTOCOL_TLS_CLIENT)
            context.expected_name = params.host
            context.load_default_certs()
        elif params.sslmode in ("prefer", "require"):
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        try:
            conn = pymysql.connect(
                host=addresses[0],
                port=params.port,
                user=params.username,
                password=params.password,
                database=params.database,
                connect_timeout=CONNECT_TIMEOUT_SECONDS,
                read_timeout=30,
                ssl=context,
                ssl_disabled=params.sslmode == "disable",
                autocommit=True,
                charset="utf8mb4",
            )
        except pymysql.err.MySQLError as exc:
            raise ConnectionFailed("could not connect to the external database") from exc
        try:
            with conn.cursor() as cur:
                if params.sslmode in ("require", "verify-full"):
                    # PyMySQL quietly carries on without TLS when the server does not offer it.
                    cur.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'")
                    row = cur.fetchone()
                    if not row or not row[1]:
                        raise ConnectionFailed("the external database does not offer an encrypted connection")
                cur.execute("SET SESSION TRANSACTION READ ONLY")
        except pymysql.err.MySQLError as exc:
            conn.close()
            raise ConnectionFailed("could not connect to the external database") from exc
        except ConnectionFailed:
            conn.close()
            raise
        return conn

    def test_connection(self, params: ConnectionParams) -> None:
        import pymysql

        conn = self._connect(params)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        except pymysql.err.MySQLError as exc:
            raise ConnectionFailed("could not connect to the external database") from exc
        finally:
            conn.close()

    def introspect_schema(self, params: ConnectionParams) -> list[TableInfo]:
        import pymysql

        conn = self._connect(params)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.TABLE_NAME, c.COLUMN_NAME, c.COLUMN_TYPE, c.IS_NULLABLE
                    FROM information_schema.COLUMNS c
                    JOIN information_schema.TABLES t
                      ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
                    WHERE c.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                    ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
                    """
                )
                rows = cur.fetchall()
        except pymysql.err.MySQLError as exc:
            raise ConnectionFailed("could not read schema from the external database") from exc
        finally:
            conn.close()
        tables: dict[str, list[ColumnInfo]] = {}
        for table_name, column_name, data_type, is_nullable in rows:
            tables.setdefault(str(table_name), []).append(
                ColumnInfo(name=str(column_name), data_type=str(data_type), is_nullable=is_nullable == "YES")
            )
        return [TableInfo(name=name, columns=cols) for name, cols in tables.items()]

    def list_rows(
        self, params: ConnectionParams, table_name: str, *, limit: int = DEFAULT_LIMIT, offset: int = 0
    ) -> dict:
        import pymysql
        from pymysql.cursors import DictCursor

        limit = max(1, min(limit, MAX_LIMIT))
        offset = max(0, offset)
        table = _mysql_identifier(table_name)
        conn = self._connect(params)
        try:
            with conn.cursor(DictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS n FROM {table}")  # noqa: S608 - quoted identifier, cross-checked name
                total = int(cur.fetchone()["n"])
                cur.execute(f"SELECT * FROM {table} LIMIT %s OFFSET %s", [limit, offset])  # noqa: S608
                rows = cur.fetchall()
        except pymysql.err.MySQLError as exc:
            raise ConnectionFailed("could not read rows from the external database") from exc
        finally:
            conn.close()
        return {"count": total, "limit": limit, "offset": offset, "results": _clean_rows(rows)}


# ---- SQL Server --------------------------------------------------------------------------------------------
def _sqlserver_identifier(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


# What each IntraForge TLS choice asks of SQL Server (FreeTDS). The driver cannot check the server's
# certificate, so "verify-full" is refused rather than quietly weakened (ConnectedDatabaseCreateSerializer
# refuses it up front too).
_SQLSERVER_ENCRYPTION = {"disable": "off", "prefer": "request", "require": "require"}


class SQLServerConnector:
    """Microsoft SQL Server 2016+ and Azure SQL, through pymssql (FreeTDS). Tables of the dbo schema."""

    def _connect(self, params: ConnectionParams):
        import pymssql

        if params.sslmode not in _SQLSERVER_ENCRYPTION:
            raise ConnectionFailed(
                "SQL Server connections can be encrypted (require) but not certificate-verified"
            )
        addresses = assert_host_is_safe(params.host)
        try:
            return pymssql.connect(
                server=addresses[0],
                port=str(params.port),
                user=params.username,
                password=params.password,
                database=params.database,
                login_timeout=CONNECT_TIMEOUT_SECONDS,
                timeout=30,
                encryption=_SQLSERVER_ENCRYPTION[params.sslmode],
                autocommit=True,
                tds_version="7.4",
            )
        except pymssql.Error as exc:
            raise ConnectionFailed("could not connect to the external database") from exc

    def test_connection(self, params: ConnectionParams) -> None:
        import pymssql

        conn = self._connect(params)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchall()
        except pymssql.Error as exc:
            raise ConnectionFailed("could not connect to the external database") from exc
        finally:
            conn.close()

    def introspect_schema(self, params: ConnectionParams) -> list[TableInfo]:
        import pymssql

        conn = self._connect(params)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS c
                JOIN INFORMATION_SCHEMA.TABLES t
                  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
                WHERE c.TABLE_SCHEMA = 'dbo'
                ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
                """
            )
            rows = cur.fetchall()
        except pymssql.Error as exc:
            raise ConnectionFailed("could not read schema from the external database") from exc
        finally:
            conn.close()
        tables: dict[str, list[ColumnInfo]] = {}
        for table_name, column_name, data_type, is_nullable in rows:
            tables.setdefault(str(table_name), []).append(
                ColumnInfo(name=str(column_name), data_type=str(data_type), is_nullable=is_nullable == "YES")
            )
        return [TableInfo(name=name, columns=cols) for name, cols in tables.items()]

    def list_rows(
        self, params: ConnectionParams, table_name: str, *, limit: int = DEFAULT_LIMIT, offset: int = 0
    ) -> dict:
        import pymssql

        limit = max(1, min(limit, MAX_LIMIT))
        offset = max(0, offset)
        table = "[dbo]." + _sqlserver_identifier(table_name)
        conn = self._connect(params)
        try:
            cur = conn.cursor(as_dict=True)
            cur.execute(f"SELECT COUNT_BIG(*) AS n FROM {table}")  # noqa: S608 - quoted identifier, cross-checked
            total = int(cur.fetchone()["n"])
            cur.execute(
                f"SELECT * FROM {table} ORDER BY (SELECT NULL) OFFSET %d ROWS FETCH NEXT %d ROWS ONLY",  # noqa: S608
                (offset, limit),
            )
            rows = cur.fetchall()
        except pymssql.Error as exc:
            raise ConnectionFailed("could not read rows from the external database") from exc
        finally:
            conn.close()
        return {"count": total, "limit": limit, "offset": offset, "results": _clean_rows(rows)}


CONNECTORS = {
    "postgresql": PostgresConnector(),
    "mysql": MySQLConnector(),
    "sqlserver": SQLServerConnector(),
}

DEFAULT_PORTS = {"postgresql": 5432, "mysql": 3306, "sqlserver": 1433}
