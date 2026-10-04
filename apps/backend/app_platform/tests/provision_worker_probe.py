"""Isolated test worker; kill its first child after tenant commit."""

import os
import signal
import sys

import django


def main():
    django.setup()
    from django.conf import settings

    from app_platform.models import RuntimeProvision
    from config.celery import app

    instance_id, marker, queue = sys.argv[1:]
    if not all(settings.DATABASES[name]["NAME"].startswith("test_") for name in ("default", "tenant")):
        raise RuntimeError("Crash probe requires isolated test databases")
    original = RuntimeProvision.save

    def save(receipt, *args, **kwargs):
        if str(receipt.instance_id) == instance_id and receipt.completed_at:
            try:
                descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
                os.kill(os.getpid(), signal.SIGKILL)
        return original(receipt, *args, **kwargs)

    RuntimeProvision.save = save
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
