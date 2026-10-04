"""The support-diagnostics redactor: a bundle handed to a supporter must never contain a secret."""

from django.test import SimpleTestCase

from system.redaction import REDACTED, redact

FERNET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFG="  # 43 url-safe chars + '=': the shape of a Fernet key


class SecretShapesAreRemovedTests(SimpleTestCase):
    def assertGone(self, secret, line):
        cleaned = redact(line)
        self.assertNotIn(secret, cleaned, cleaned)
        self.assertIn(REDACTED, cleaned)

    def test_env_style_assignments_keep_the_name_and_drop_the_value(self):
        for name in (
            "DJANGO_SECRET_KEY",
            "POSTGRES_PASSWORD",
            "MINIO_ROOT_PASSWORD",
            "CREDENTIAL_ENCRYPTION_KEY",
            "BACKUP_ENCRYPTION_KEY",
            "AWS_SECRET_ACCESS_KEY",
            "API_TOKEN",
            "X-Api-Key",
        ):
            with self.subTest(name):
                cleaned = redact(f"{name}=s3cr3t-Value_123")
                self.assertNotIn("s3cr3t-Value_123", cleaned)
                self.assertTrue(
                    cleaned.startswith(name), cleaned
                )  # the name stays: it shows the setting exists

    def test_json_and_quoted_values(self):
        for line in ('{"password": "hunter2xyz"}', "password: 'hunter2xyz'", 'signing_secret="hunter2xyz"'):
            with self.subTest(line):
                self.assertGone("hunter2xyz", line)

    def test_bearer_and_basic_credentials(self):
        self.assertGone("abcDEF123456789xyz", "Authorization: Bearer abcDEF123456789xyz")
        self.assertGone("dXNlcjpwYXNzd29yZA", "GET /x HTTP/1.1 Basic dXNlcjpwYXNzd29yZA==")

    def test_credentials_inside_a_url_are_removed_but_the_host_survives(self):
        cleaned = redact("connecting to postgres://intraforge:pa55w0rd@postgres-control:5432/app")
        self.assertNotIn("pa55w0rd", cleaned)
        self.assertIn("postgres-control:5432/app", cleaned)
        self.assertIn("intraforge:", cleaned)

    def test_session_and_csrf_cookies(self):
        cleaned = redact("Cookie: sessionid=abc123def456; csrftoken=zzz999yyy888")
        self.assertNotIn("abc123def456", cleaned)
        self.assertNotIn("zzz999yyy888", cleaned)

    def test_a_jwt(self):
        token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        self.assertGone(token, f"token was {token} here")

    def test_a_fernet_key_wherever_it_appears(self):
        self.assertGone(FERNET, f"loaded key {FERNET} ok")

    def test_a_multiline_private_key_block(self):
        block = (
            "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\nabcdefghijklmnop\n"
            "-----END PRIVATE KEY-----"
        )
        cleaned = redact(f"before\n{block}\nafter")
        self.assertNotIn("MIIEvQ", cleaned)
        self.assertIn("before", cleaned)
        self.assertIn("after", cleaned)


class OrdinaryDiagnosticsSurviveTests(SimpleTestCase):
    def test_lines_a_supporter_needs_are_left_alone(self):
        for line in (
            "2026-09-20 10:00:01 INFO gunicorn Booting worker with pid: 42",
            '{"level": "WARNING", "logger": "django.request", "message": "Forbidden: /api/v1/x/records/"}',
            "database:default ok, database:tenant ok, valkey ok",
            "Applying sharing.0002_inventory_operation_levels... OK",
            "backup 88e692be-49cd-473e-88ae-459a93044c2b succeeded (4212694 bytes)",
            "restore took 53 s; sha256 f769cb61c09dcb9f",
            "POST /api/v1/app-instances/03cc2c19-72da-4765-9a4b-5f7a6bd2b455/operations/sell/ 201",
        ):
            with self.subTest(line):
                self.assertEqual(redact(line), line)
