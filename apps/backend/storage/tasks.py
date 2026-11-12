from celery import shared_task


@shared_task
def clean_up_storage() -> dict:
    """The nightly cleanup of every bucket (storage.services.clean_up_bucket)."""
    from .models import Bucket
    from .services import clean_up_bucket

    totals = {"files": 0, "versions": 0, "bytes": 0}
    for bucket in Bucket.objects.select_related("project__workspace").exclude(trash_days=0, version_days=0):
        for key, value in clean_up_bucket(bucket).items():
            totals[key] += value
    return totals
