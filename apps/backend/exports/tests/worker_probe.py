"""Test-only prefork worker: kill one child at a selected restore boundary.

Executed only by test_restore_recovery with isolated test DBs and queue.
The local marker controls fault injection, NOT application correctness.
"""

import os
import signal
import sys
from pathlib import Path

import django


def main():
    django.setup()
    from django.conf import settings

    from config.celery import app
    from exports import recovery
    from exports.models import RestoreJob

    job_id, boundary, marker_path, queue = sys.argv[1:]
    if not all(settings.DATABASES[alias]["NAME"].startswith("test_") for alias in ("default", "tenant")):
        raise RuntimeError("Worker crash probe requires isolated test databases")

    def kill_once():
        try:
            descriptor = os.open(marker_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return
        os.close(descriptor)
        os.kill(os.getpid(), signal.SIGKILL)

    if boundary == "tenant_commit":
        original_save = RestoreJob.save

        def save(instance, *args, **kwargs):
            if str(instance.id) == job_id and instance.status == "completed":
                kill_once()
            return original_save(instance, *args, **kwargs)

        RestoreJob.save = save
    elif boundary == "completed":
        original_cleanup = recovery.cleanup_completed_source

        def cleanup(job):
            if str(job.id) == job_id:
                kill_once()
            return original_cleanup(job)

        recovery.cleanup_completed_source = cleanup
    else:
        raise ValueError("Unknown probe boundary")
    if Path(marker_path).exists():
        raise RuntimeError("Probe marker must be fresh")
    app.conf.update(task_always_eager=False)
    app.worker_main(
        [
            "worker",
            "--pool=prefork",
            "--concurrency=1",
            f"--queues={queue}",
            f"--hostname={queue}@%h",
            "--without-gossip",
            "--without-mingle",
            "--without-heartbeat",
            "--loglevel=INFO",
        ]
    )


if __name__ == "__main__":
    main()
