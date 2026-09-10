"""Runtime preflight, reservation and asynchronous provisioning status."""

from django.http import Http404
from rest_framework import serializers
from rest_framework.response import Response

from . import provisioning
from .access import get_owned, require_manage
from .definitions import StrictSerializer
from .instances import validated
from .models import AppInstance, RuntimeProvision
from .runtime_plan import plan_runtime
from .tasks import provision_runtime_task
from .views import FoundationView


class RuntimePlan(FoundationView):
    def get(self, request, object_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        return Response(plan_runtime(request.user, instance))


class ProvisionInput(StrictSerializer):
    fingerprint = serializers.RegexField(r"\A[0-9a-f]{64}\Z", max_length=64)


class Runtime(FoundationView):
    def get(self, request, object_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        require_manage(request.user, instance)
        try:
            receipt = RuntimeProvision.objects.get(instance=instance)
        except RuntimeProvision.DoesNotExist as exc:
            raise Http404 from exc
        return Response(provisioning.status(receipt))

    def post(self, request, object_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        values = validated(ProvisionInput, request.data)
        receipt = provisioning.reserve(request.user, instance, values["fingerprint"])
        if not receipt.completed_at:
            # Reservation has committed before enqueue. A broker outage leaves
            # it retryable by repeating POST; no DDL runs in the web worker.
            provision_runtime_task.delay(str(instance.id), str(request.user.id))
        return Response(provisioning.status(receipt), status=200 if receipt.completed_at else 202)
