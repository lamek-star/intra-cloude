from django.test import SimpleTestCase

from databases.identifiers import IdentifierError, validate_column_name, validate_identifier


class ValidateIdentifierTests(SimpleTestCase):
    def test_accepts_simple_snake_case(self):
        self.assertEqual(validate_identifier("customers"), "customers")
        self.assertEqual(validate_identifier("order_line_items"), "order_line_items")
        self.assertEqual(validate_identifier("a"), "a")
        self.assertEqual(validate_identifier("a" * 63), "a" * 63)

    def test_rejects_too_long(self):
        with self.assertRaises(IdentifierError):
            validate_identifier("a" * 64)

    def test_rejects_leading_digit(self):
        with self.assertRaises(IdentifierError):
            validate_identifier("1table")

    def test_rejects_uppercase(self):
        with self.assertRaises(IdentifierError):
            validate_identifier("Customers")

    def test_rejects_empty(self):
        with self.assertRaises(IdentifierError):
            validate_identifier("")

    def test_rejects_non_string(self):
        with self.assertRaises(IdentifierError):
            validate_identifier(None)  # type: ignore[arg-type]

    # Direct SQL-injection-shaped attempts — must be rejected outright by
    # the regex, independent of whatever quoting happens downstream
    # (defense layer 1 of 2, per databases/identifiers.py's docstring).
    def test_rejects_sql_injection_attempts(self):
        attempts = [
            "customers; DROP TABLE users;--",
            "customers' OR '1'='1",
            'customers" ; DROP SCHEMA public CASCADE; --',
            "customers/*",
            "customers--",
            "customers\n",
            "customers ",
            " customers",
            "cust omers",
            "customers)",
            "customers(",
        ]
        for value in attempts:
            with self.subTest(value=value), self.assertRaises(IdentifierError):
                validate_identifier(value)


class ValidateColumnNameTests(SimpleTestCase):
    def test_accepts_ordinary_name(self):
        self.assertEqual(validate_column_name("email"), "email")

    def test_rejects_reserved_id(self):
        with self.assertRaises(IdentifierError):
            validate_column_name("id")
