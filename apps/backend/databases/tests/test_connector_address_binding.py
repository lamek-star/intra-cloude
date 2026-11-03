"""DNS validation must bind the actual connection, including strict mode."""

import socket
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from databases.connectors import ConnectionParams, UnsafeHost, _connect


def answers(*addresses):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0)) for address in addresses]


class AddressBindingTests(SimpleTestCase):
    def setUp(self):
        self.params = ConnectionParams("db.example.test", 5432, "business", "reader", "secret", "verify-full")

    def test_driver_receives_validated_address_and_original_tls_hostname(self):
        with (
            patch("databases.connectors.socket.getaddrinfo", return_value=answers("8.8.8.8")) as dns,
            patch("databases.connectors.psycopg.connect") as connect,
        ):
            _connect(self.params)
        self.assertEqual(dns.call_count, 1)
        self.assertEqual(connect.call_args.kwargs["hostaddr"], "8.8.8.8")
        self.assertEqual(connect.call_args.kwargs["host"], self.params.host)
        self.assertEqual(connect.call_args.kwargs["sslmode"], "verify-full")

    def test_mixed_safe_and_metadata_answer_never_connects(self):
        with (
            patch(
                "databases.connectors.socket.getaddrinfo", return_value=answers("8.8.8.8", "169.254.169.254")
            ),
            patch("databases.connectors.psycopg.connect") as connect,
            self.assertRaises(UnsafeHost),
        ):
            _connect(self.params)
        connect.assert_not_called()

    @override_settings(CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS=True)
    def test_ipv4_mapped_ipv6_private_address_is_rejected(self):
        with (
            patch("databases.connectors.socket.getaddrinfo", return_value=answers("::ffff:127.0.0.1")),
            patch("databases.connectors.psycopg.connect") as connect,
            self.assertRaises(UnsafeHost),
        ):
            _connect(self.params)
        connect.assert_not_called()

    def test_empty_resolution_never_falls_back_to_driver_dns(self):
        with (
            patch("databases.connectors.socket.getaddrinfo", return_value=[]),
            patch("databases.connectors.psycopg.connect") as connect,
            self.assertRaises(UnsafeHost),
        ):
            _connect(self.params)
        connect.assert_not_called()
