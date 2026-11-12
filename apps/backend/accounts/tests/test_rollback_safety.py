"""An upgrade that fails rolls back to the previous release, which then runs on the already-migrated
database. Every column a release adds must therefore have a database default, or the previous release's
inserts (which do not name the column) fail. These are the columns 1.5.1 and 1.5.6 add."""

from django.db import connection
from django.test import TestCase

from accounts.models import User
from sites.models import InternetGateway, Site
from storage.models import Bucket

NEW_COLUMNS = [
    (User, "passkey_only"),
    (Site, "internet_auto"),
    (InternetGateway, "auto_domain"),
    (User, "must_change_password"),
    (Bucket, "trash_days"),
    (Bucket, "version_days"),
]
NEW_USER_FIELDS = {"passkey_only", "must_change_password"}


class RollbackSafetyTests(TestCase):
    def test_every_new_column_has_a_database_default(self):
        with connection.cursor() as cursor:
            for model, column in NEW_COLUMNS:
                cursor.execute(
                    "SELECT is_nullable, column_default FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = %s",
                    [model._meta.db_table, column],
                )
                nullable, default = cursor.fetchone()
                with self.subTest(table=model._meta.db_table, column=column):
                    self.assertTrue(
                        nullable == "YES" or default is not None, "NOT NULL without a database default"
                    )

    def test_the_previous_release_can_still_create_a_user(self):
        # An insert that names neither new column, as the previous release's User model does.
        columns = [f.column for f in User._meta.concrete_fields if f.name not in NEW_USER_FIELDS]
        values = {
            "id": "00000000-0000-0000-0000-000000000001",
            "email": "old-release@example.com",
            "password": "!",
            "first_name": "",
            "last_name": "",
            "is_active": True,
            "mfa_enabled": False,
        }
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {User._meta.db_table} ({', '.join(columns)}) "  # noqa: S608 - fixed model columns
                f"VALUES ({', '.join('now()' if c == 'date_joined' else '%s' for c in columns)})",
                [values.get(c) for c in columns if c != "date_joined"],
            )
        old = User.objects.get(email="old-release@example.com")
        self.assertFalse(old.passkey_only)
        self.assertFalse(old.must_change_password)
