"""Template services: validated drafts and serialized immutable publication."""

import hashlib
import json

from django.db import transaction
from rest_framework import serializers

from audit import services as audit

from .access import check
from .definitions import StrictSerializer, validate_definition
from .models import AppTemplate, AppTemplateVersion


class TemplateInput(StrictSerializer):
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    description = serializers.CharField(max_length=10000, allow_blank=True, required=False)
    draft = serializers.JSONField(required=False)
    archived = serializers.BooleanField(required=False)

    def validate_draft(self, value):
        return validate_definition(value)


def create_template(actor, organization, data):
    check(actor, organization.id, "app_template.manage")
    serializer = TemplateInput(data=data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        template = AppTemplate.objects.create(
            organization=organization,
            created_by=actor,
            **serializer.validated_data,
        )
        event(actor, template, "create")
    return template


def update_template(actor, template, data):
    check(actor, template.organization_id, "app_template.manage", ("app_template", template.id))
    serializer = TemplateInput(data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        template = AppTemplate.objects.select_for_update().get(pk=template.pk)
        for key, value in serializer.validated_data.items():
            setattr(template, key, value)
        template.save()
        event(actor, template, "update")
    return template


def publish_template(actor, template):
    check(actor, template.organization_id, "app_template.publish", ("app_template", template.id))
    with transaction.atomic():
        template = AppTemplate.objects.select_for_update().get(pk=template.pk)
        if template.archived:
            raise serializers.ValidationError("Archived templates cannot be published.")
        definition = validate_definition(template.draft)
        # Persist generated IDs so subsequent publications retain definition lineage.
        template.draft = definition
        template.save(update_fields=["draft"])
        latest = template.versions.order_by("-number").first()
        version = AppTemplateVersion.objects.create(
            template=template,
            number=latest.number + 1 if latest else 1,
            definition=definition,
            created_by=actor,
            checksum_sha256=hashlib.sha256(
                json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        )
        event(actor, template, "publish", {"version_id": str(version.id), "number": version.number})
    return version


def event(actor, template, action, context=None):
    audit.record(
        actor=actor,
        organization_id=template.organization_id,
        action=f"app_template.{action}",
        resource_type="app_template",
        resource_id=template.id,
        context=context,
    )
