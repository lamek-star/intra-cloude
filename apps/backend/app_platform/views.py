"""Small metadata endpoints. Mutations and permission checks stay in services."""

from django.db.models import Model, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer as DRFModelSerializer
from rest_framework.views import APIView

from organizations.services import get_member_organization
from permissions.models import ResourceGrant
from permissions.services import has_permission
from workspaces.views import get_member_project

from . import instances, templates
from .access import check, get_owned
from .models import (
    AppInstance,
    AppTemplate,
    AppTemplateVersion,
    FieldDefinition,
    ModelDefinition,
    RelationshipDefinition,
)
from .serializers import (
    FieldSerializer,
    InstanceSerializer,
    ModelSerializer,
    RelationshipSerializer,
    TemplateSerializer,
    VersionSerializer,
)


class FoundationView(APIView):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_active or hasattr(request.user, "service_account"):
            raise PermissionDenied("Foundation administration requires a human session.")

    def page(self, request, queryset, serializer):
        paginator = LimitOffsetPagination()
        paginator.default_limit = 50
        paginator.max_limit = 100
        return paginator.get_paginated_response(
            serializer(paginator.paginate_queryset(queryset, request), many=True).data
        )


def readable(queryset, actor, org_id, resource_type, capability):
    if has_permission(actor, capability, organization_id=org_id):
        return queryset
    grants = ResourceGrant.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
        user=actor,
        organization_id=org_id,
        resource_type=resource_type,
        permission_id=capability,
    ).values("resource_id")
    return queryset.filter(id__in=grants)


def read_template(actor, template):
    check(actor, template.organization_id, "app_template.read", ("app_template", template.id))


def read_instance(actor, instance):
    check(actor, instance.organization_id, "app_instance.read", ("app_instance", instance.id))


class TemplateList(FoundationView):
    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        rows = readable(
            AppTemplate.objects.filter(organization=org),
            request.user,
            org.id,
            "app_template",
            "app_template.read",
        )
        return self.page(request, rows, TemplateSerializer)

    def post(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        return Response(
            TemplateSerializer(templates.create_template(request.user, org, request.data)).data, status=201
        )


class TemplateDetail(FoundationView):
    def get(self, request, object_id):
        obj = get_owned(AppTemplate, object_id, request.user, "organization")
        read_template(request.user, obj)
        return Response(TemplateSerializer(obj).data)

    def patch(self, request, object_id):
        obj = get_owned(AppTemplate, object_id, request.user, "organization")
        return Response(TemplateSerializer(templates.update_template(request.user, obj, request.data)).data)


class VersionList(FoundationView):
    def get(self, request, object_id):
        obj = get_owned(AppTemplate, object_id, request.user, "organization")
        read_template(request.user, obj)
        return self.page(request, obj.versions.all(), VersionSerializer)

    def post(self, request, object_id):
        obj = get_owned(AppTemplate, object_id, request.user, "organization")
        if request.data:
            raise ValidationError("Publish accepts an empty object; edit the draft separately.")
        return Response(VersionSerializer(templates.publish_template(request.user, obj)).data, status=201)


class VersionDetail(FoundationView):
    def get(self, request, object_id):
        obj = get_owned(AppTemplateVersion, object_id, request.user, "template__organization")
        read_template(request.user, obj.template)
        return Response(VersionSerializer(obj).data)


class InstanceList(FoundationView):
    def get(self, request, project_id):
        project = get_member_project(request.user, project_id)
        rows = readable(
            project.app_instances.all(),
            request.user,
            project.workspace.organization_id,
            "app_instance",
            "app_instance.read",
        )
        return self.page(request, rows, InstanceSerializer)

    def post(self, request, project_id):
        project = get_member_project(request.user, project_id)
        return Response(
            InstanceSerializer(instances.install(request.user, project, request.data)).data, status=201
        )


class InstanceDetail(FoundationView):
    def get(self, request, object_id):
        obj = get_owned(AppInstance, object_id, request.user, "organization")
        read_instance(request.user, obj)
        return Response(InstanceSerializer(obj).data)

    def patch(self, request, object_id):
        obj = get_owned(AppInstance, object_id, request.user, "organization")
        return Response(InstanceSerializer(instances.update_instance(request.user, obj, request.data)).data)


class ModelList(FoundationView):
    def get(self, request, object_id):
        obj = get_owned(AppInstance, object_id, request.user, "organization")
        read_instance(request.user, obj)
        return self.page(request, obj.models.all(), ModelSerializer)

    def post(self, request, object_id):
        obj = get_owned(AppInstance, object_id, request.user, "organization")
        return Response(
            ModelSerializer(instances.add_model(request.user, obj, request.data)).data, status=201
        )


class FieldList(FoundationView):
    def get(self, request, object_id):
        obj = get_owned(ModelDefinition, object_id, request.user, "instance__organization")
        read_instance(request.user, obj.instance)
        return self.page(request, obj.fields.all(), FieldSerializer)

    def post(self, request, object_id):
        obj = get_owned(ModelDefinition, object_id, request.user, "instance__organization")
        return Response(
            FieldSerializer(instances.add_field(request.user, obj, request.data)).data, status=201
        )


class RelationshipList(FoundationView):
    def get(self, request, object_id):
        obj = get_owned(AppInstance, object_id, request.user, "organization")
        read_instance(request.user, obj)
        return self.page(request, obj.relationships.all(), RelationshipSerializer)

    def post(self, request, object_id):
        obj = get_owned(AppInstance, object_id, request.user, "organization")
        return Response(
            RelationshipSerializer(instances.add_relationship(request.user, obj, request.data)).data,
            status=201,
        )


class DefinitionDetail(FoundationView):
    model: type[Model] = ModelDefinition
    serializer: type[DRFModelSerializer] = ModelSerializer
    organization_path = "instance__organization"

    def get(self, request, object_id):
        obj = get_owned(self.model, object_id, request.user, self.organization_path)
        instance = obj.model.instance if isinstance(obj, FieldDefinition) else obj.instance
        read_instance(request.user, instance)
        return Response(self.serializer(obj).data)

    def patch(self, request, object_id):
        obj = get_owned(self.model, object_id, request.user, self.organization_path)
        return Response(self.serializer(instances.update_definition(request.user, obj, request.data)).data)


class FieldDetail(DefinitionDetail):
    model = FieldDefinition
    serializer = FieldSerializer
    organization_path = "model__instance__organization"


class RelationshipDetail(DefinitionDetail):
    model = RelationshipDefinition
    serializer = RelationshipSerializer
