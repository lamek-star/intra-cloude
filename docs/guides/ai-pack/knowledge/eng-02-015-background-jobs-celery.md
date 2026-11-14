# Chapter 2 — The backend — Background jobs (Celery)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 2 — The backend.

`worker` runs tasks from Valkey; `beat` schedules the periodic ones (`config/celery.py`). Long tasks set
`acks_late=True` with a visibility timeout longer than the task, so a worker that dies mid-task has the task delivered
again — and every such task is written to be safe to run twice (imports keep a checkpoint; exports and restores carry
idempotency keys and operation-derived ids; webhooks de-duplicate by event id). Schedules: backups nightly
(02:00–02:50), restore tests weekly, health checks every 5 minutes, webhook retries with back-off.
