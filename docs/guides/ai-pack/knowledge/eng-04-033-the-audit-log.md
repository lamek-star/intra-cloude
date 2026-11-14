# Chapter 4 — Security and permissions — The audit log

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

`audit.services.record(...)` writes who, what, which resource, the result (`success`, `denied`, `error`) and the request
id. The model refuses updates and deletes. Denied attempts are recorded too. Organization admins and auditors read it
at `/orgs/[orgId]/audit`.
