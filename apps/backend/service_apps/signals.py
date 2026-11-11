from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from .sessions import revoke_for_django_session


@receiver(user_logged_out)
def end_application_sessions(sender, request, user, **kwargs):
    """Logging out of IntraForge ends every application session opened from that login.
    (Introspection would refuse them anyway once the Django session is gone; revoking here makes
    the record say so explicitly.)"""
    key = getattr(getattr(request, "session", None), "session_key", None)
    if key:
        revoke_for_django_session(key)
