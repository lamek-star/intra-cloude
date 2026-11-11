from rest_framework import serializers

from organizations.models import Membership

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    # H15: who did it, readable -- the person's email, or the application's name for a request made
    # with an application key. Only for accounts of the event's own organization; anything else is
    # described without naming it.
    actor_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "timestamp",
            "actor",
            "actor_display",
            "organization",
            "action",
            "resource_type",
            "resource_id",
            "request_id",
            "result",
            "context",
        ]
        read_only_fields = fields

    def _member_ids(self, organization_id) -> set:
        cache = self.context.setdefault("_audit_member_ids", {})
        if organization_id not in cache:
            cache[organization_id] = set(
                Membership.objects.filter(organization_id=organization_id).values_list("user_id", flat=True)
            )
        return cache[organization_id]

    def get_actor_display(self, event: AuditEvent) -> str:
        actor = event.actor
        if actor is None:
            return "System"
        service_account = getattr(actor, "service_account", None)
        if service_account is not None:
            application = service_account.application
            if application.organization_id == event.organization_id:
                return f"{application.name} (application)"
            return "An application of another organization"
        if event.organization_id is not None and actor.id in self._member_ids(event.organization_id):
            return actor.email
        return "An account outside this organization"
