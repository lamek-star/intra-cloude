"""Bounded webhook POST transport: validated numeric destination, no redirects/proxy.

Keep the original hostname for HTTP Host and TLS verification/SNI, while
connecting the socket directly to the address checked by the shared policy.
"""

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit

from databases.connectors import UnsafeHost, assert_host_is_safe


class DeliveryRejected(Exception):
    pass


def _socket(address: str, port: int, timeout: float) -> socket.socket:
    family = socket.AF_INET6 if ipaddress.ip_address(address).version == 6 else socket.AF_INET
    connection = socket.socket(family, socket.SOCK_STREAM)
    try:
        connection.settimeout(timeout)
        connection.connect((address, port))
        return connection
    except BaseException:
        connection.close()
        raise


def post(url: str, body: bytes, headers: dict[str, str], *, timeout: float = 5) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeHost("webhook requires an HTTP(S) URL without credentials")
    address = assert_host_is_safe(parsed.hostname)[0]
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    # HTTPConnection only formats the request. Supplying the connected socket
    # prevents its connect() from resolving the hostname again.
    connection = http.client.HTTPConnection(parsed.hostname, port, timeout=timeout)
    try:
        connection.sock = _socket(address, port, timeout)
        if parsed.scheme == "https":
            connection.sock = ssl.create_default_context().wrap_socket(
                connection.sock, server_hostname=parsed.hostname
            )
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        connection.request("POST", target, body=body, headers=headers)
        response = connection.getresponse()
        # Never follow redirects (including to metadata/LAN targets). Do not
        # read an untrusted, potentially unbounded response body.
        if not 200 <= response.status < 300:
            raise DeliveryRejected(f"Receiver returned HTTP {response.status}")
    finally:
        connection.close()
