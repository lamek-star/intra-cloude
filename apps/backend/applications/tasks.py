from celery import shared_task


@shared_task
def prune_api_request_log() -> int:
    """Deletes application request-log rows older than API_REQUEST_LOG_DAYS."""
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    from .models import ApiRequestLog

    cutoff = timezone.now() - timedelta(days=settings.API_REQUEST_LOG_DAYS)
    deleted, _ = ApiRequestLog.objects.filter(at__lt=cutoff).delete()
    return deleted
