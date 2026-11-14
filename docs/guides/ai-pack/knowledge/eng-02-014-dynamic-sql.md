# Chapter 2 — The backend — Dynamic SQL

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 2 — The backend.

Tables, columns and constraints that people create are real PostgreSQL objects. The rules (`databases/identifiers.py`,
`ddl.py`, `rows.py`):

- identifiers are validated against a strict pattern and a reserved-word list before use;
- every identifier is quoted with `psycopg.sql.Identifier`, every value is a bound parameter — never string formatting;
- DDL runs in a transaction after the permission check and writes an audit event;
- reads are capped (rows and bytes) so one request cannot exhaust the server.
