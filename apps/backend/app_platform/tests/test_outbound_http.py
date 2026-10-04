import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from django.test import SimpleTestCase

from app_platform import outbound_http


class OutboundHTTPTests(SimpleTestCase):
    def test_connects_only_to_validated_address_and_preserves_host(self):
        with patch.object(outbound_http, "assert_host_is_safe", return_value=("93.184.216.34",)) as resolve:
            with patch.object(outbound_http, "_socket") as connect:
                with patch.object(outbound_http.http.client, "HTTPConnection") as http:
                    http.return_value.getresponse.return_value.status = 204
                    outbound_http.post("http://example.test:8080/hook?q=1", b"{}", {})
        resolve.assert_called_once_with("example.test")
        connect.assert_called_once_with("93.184.216.34", 8080, 5)
        http.assert_called_once_with("example.test", 8080, timeout=5)
        http.return_value.request.assert_called_once_with("POST", "/hook?q=1", body=b"{}", headers={})

    def test_redirect_is_rejected_without_visiting_destination(self):
        visits = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                visits.append(self.path)
                self.send_response(307)
                self.send_header("Location", "/forbidden")
                self.end_headers()

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(outbound_http.DeliveryRejected):
                outbound_http.post(f"http://127.0.0.1:{server.server_port}/original", b"{}", {})
            self.assertEqual(visits, ["/original"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
