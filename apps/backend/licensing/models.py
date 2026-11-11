"""This installation's licence (ADR-0023): one row."""

from django.conf import settings
from django.db import models


class LicenseState(models.Model):
    trial_started_at = models.DateTimeField()
    # The latest time IntraForge has seen: a clock set back by more than a day is noticed.
    last_seen_at = models.DateTimeField()
    serial = models.CharField(max_length=40, blank=True)
    activation_code = models.TextField(blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self) -> str:
        return self.serial or "trial"
