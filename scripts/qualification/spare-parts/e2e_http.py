"""End-to-end check of the Spare Parts service application through the real proxy (qualification stack)."""
import http.cookiejar
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://localhost:8444"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


class Browser:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx), urllib.request.HTTPCookieProcessor(self.jar)
        )

    def cookie(self, name):
        for c in self.jar:
            if c.name == name:
                return c
        return None

    def req(self, method, path, body=None, headers=None, raw=False):
        h = {"Origin": BASE, "Referer": BASE + "/"}
        csrf = self.cookie("csrftoken")
        if csrf and method != "GET":
            h["X-CSRFToken"] = csrf.value
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
        try:
            with self.opener.open(r, timeout=60) as resp:
                content = resp.read()
                return resp.status, (content if raw else _j(content)), dict(resp.headers)
        except urllib.error.HTTPError as e:
            content = e.read()
            return e.code, (content if raw else _j(content)), dict(e.headers)


def _j(b):
    try:
        return json.loads(b or b"null")
    except ValueError:
        return b[:200]


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        check.failed += 1


check.failed = 0
