# ADR-0024: MySQL/MariaDB and SQL Server connected databases

Status: accepted; implemented (2026-11-12).

## Problem

ADR-0009 built connected mode (read-only access to an outside database) for PostgreSQL first and listed MySQL/MariaDB
and SQL Server as later work. Shops keep their old point-of-sale or accounting data in exactly those databases.

## Decision

1. **Same connector interface, same rules** (`databases/connectors.py`): test the connection, read the schema, page
   through rows. The host passes the SSRF guard on every connection and the connection goes to the address that was
   checked; only `SELECT` is sent; a table name is checked against a fresh schema read and quoted by the engine's own
   rules (backticks for MySQL, brackets for SQL Server); binary columns are returned as their size, never their bytes.
2. **Drivers:** `PyMySQL` (pure Python, MIT) for MySQL 5.7+/8.x and MariaDB; `pymssql` (LGPL, bundles FreeTDS) for SQL
   Server 2016+ and Azure SQL. Both are wheels with no system packages, pinned in `requirements/base.txt`. pyodbc was
   not chosen: it needs Microsoft's ODBC driver installed in the image.
3. **Read only, twice:** besides only sending `SELECT`, a MySQL session is set `READ ONLY`. Owners should still give
   IntraForge a database user that may only read (the form says so).
4. **TLS:** MySQL honours all four modes; `verify-full` checks the certificate against the host's *name* even though
   the connection goes to the checked address. FreeTDS cannot verify a SQL Server certificate, so `verify-full` is
   refused for SQL Server (in the API and the form) instead of being quietly weakened; `require` encrypts.
5. **Scope:** MySQL shows the connected database's tables and views; SQL Server the `dbo` schema.

## Consequences

- Two more runtime dependencies to audit each release (`pip-audit`); `pymssql`'s LGPL text and FreeTDS notice go in
  the release notices (THIRD_PARTY_LICENSES.md).
- Verified against real servers (MySQL 8.4, SQL Server 2022 Developer) in `databases/tests/test_other_engines.py`;
  those tests skip when the servers are not given (`IF_TEST_MYSQL`, `IF_TEST_MSSQL`).
