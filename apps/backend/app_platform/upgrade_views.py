"""Phase 9 -- template versioning and upgrade endpoints."""

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import upgrades
from .access import get_owned
from .models import AppInstance
from .serializers import UpgradeSerializer
from .views import FoundationView, read_instance


class UpgradeView(FoundationView):
    """GET previews a three-way diff against a target template version
    without changing anything; POST applies it (additions and safe label
    syncs only -- see upgrades.py for exactly what "safe" means and why).
    Human-session-only: an upgrade is schema administration, the same bar
    every other schema-mutating endpoint in this app already holds (see
    FoundationView's own docstring for why these stay out of
    `service_account_methods`)."""

    def get(self, request, object_id, version_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        return Response(upgrades.preview_upgrade(request.user, instance, version_id))

    def post(self, request, object_id, version_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        if request.data:
            raise ValidationError("Upgrade accepts an empty body; the target version is in the URL.")
        upgrade = upgrades.apply_upgrade(request.user, instance, version_id)
        return Response(UpgradeSerializer(upgrade).data, status=201)


class UpgradeHistoryList(FoundationView):
    def get(self, request, object_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        read_instance(request.user, instance)
        return self.page(request, instance.upgrades.all(), UpgradeSerializer)
