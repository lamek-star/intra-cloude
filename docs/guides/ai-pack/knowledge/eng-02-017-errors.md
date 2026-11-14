# Chapter 2 — The backend — Errors

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 2 — The backend.

`system/exceptions.py` turns errors into `{"error": {"code": …, "message": …, "request_id": …}}`. A stack trace is never
sent to the browser; it is logged with the request id, which the screen can show under "View technical details".
