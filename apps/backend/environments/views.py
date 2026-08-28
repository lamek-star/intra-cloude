from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.models import ApplicationCredential
from applications.serializers import ApplicationCredentialSerializer
from applications.views import get_member_application
from databases.models import TenantDatabase
from storage.models import Bucket

from . import services
from .models import Environment, EnvironmentSecret, EnvironmentVariable, EnvironmentWebhook
from .serializers import (
    DatabaseBindingSerializer,
    EnvironmentCloneSerializer,
    EnvironmentCreateSerializer,
    EnvironmentCredentialIssueSerializer,
    EnvironmentDeleteSerializer,
    EnvironmentSecretSerializer,
    EnvironmentSecretWriteSerializer,
    EnvironmentSerializer,
    EnvironmentUpdateSerializer,
    EnvironmentVariableSerializer,
    EnvironmentVariableWriteSerializer,
    EnvironmentWebhookCreateSerializer,
    EnvironmentWebhookSerializer,
    EnvironmentWebhookUpdateSerializer,
    StorageBindingSerializer,
)


def _forbidden():
    return Response(status=status.HTTP_403_FORBIDDEN)


class EnvironmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        application = get_member_application(request.user, application_id)
        environments = Environment.objects.filter(application=application).select_related(
            "tenant_database", "bucket"
        )
        return Response(EnvironmentSerializer(environments, many=True).data)

    def post(self, request, application_id):
        application = get_member_application(request.user, application_id)
        # Creation itself only needs environment.manage at the
        # organization level (there's no existing Environment resource
        # yet to scope a ResourceGrant to, and a brand-new environment is
        # never production-tier unless the caller explicitly says so --
        # checked below once we know is_production_tier).
        from permissions.services import has_permission

        if not has_permission(
            request.user, "environment.manage", organization_id=application.organization_id
        ):
            return _forbidden()

        serializer = EnvironmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        is_production_tier = data["is_production_tier"]
        if is_production_tier is None:
            is_production_tier = data["environment_type"] == "production"
        if is_production_tier and not has_permission(
            request.user, "environment.production.manage", organization_id=application.organization_id
        ):
            return _forbidden()

        environment = services.create_environment(
            application=application,
            name=data["name"],
            environment_type=data["environment_type"],
            is_production_tier=is_production_tier,
            config=data["config"],
            actor=request.user,
        )
        return Response(EnvironmentSerializer(environment).data, status=status.HTTP_201_CREATED)


class EnvironmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.read"):
            return _forbidden()
        return Response(EnvironmentSerializer(environment).data)

    def patch(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        serializer = EnvironmentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # Switching a non-production environment to production-tier
        # requires the caller to already hold environment.production.manage
        # -- otherwise a Developer could promote their way past the gate.
        if serializer.validated_data.get("is_production_tier") and not environment.is_production_tier:
            from permissions.services import has_permission

            if not has_permission(
                request.user, "environment.production.manage", organization_id=environment.organization_id
            ):
                return _forbidden()
        environment = services.update_environment(
            environment=environment, actor=request.user, **serializer.validated_data
        )
        return Response(EnvironmentSerializer(environment).data)

    def delete(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        serializer = EnvironmentDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.delete_environment(
                environment=environment,
                actor=request.user,
                confirm_name=serializer.validated_data["confirm_name"],
                confirm_production_understanding=serializer.validated_data["confirm_production_understanding"],
            )
        except services.EnvironmentValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EnvironmentCloneView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        serializer = EnvironmentCloneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clone = services.clone_environment(
            environment=environment, actor=request.user, name=serializer.validated_data["name"]
        )
        return Response(EnvironmentSerializer(clone).data, status=status.HTTP_201_CREATED)


class EnvironmentDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        environment = services.set_environment_status(
            environment=environment, actor=request.user, status=Environment.Status.DISABLED
        )
        return Response(EnvironmentSerializer(environment).data)


class EnvironmentEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        environment = services.set_environment_status(
            environment=environment, actor=request.user, status=Environment.Status.ACTIVE
        )
        return Response(EnvironmentSerializer(environment).data)


class EnvironmentVariableListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.read"):
            return _forbidden()
        return Response(EnvironmentVariableSerializer(environment.variables.all(), many=True).data)

    def post(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        serializer = EnvironmentVariableWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variable = services.set_variable(
            environment=environment,
            key=serializer.validated_data["key"],
            value=serializer.validated_data["value"],
            actor=request.user,
        )
        return Response(EnvironmentVariableSerializer(variable).data, status=status.HTTP_201_CREATED)


def _get_member_variable(user, environment_id, variable_id) -> EnvironmentVariable:
    environment = services.get_member_environment(user, environment_id)
    try:
        return environment.variables.get(id=variable_id)
    except EnvironmentVariable.DoesNotExist as exc:
        raise Http404 from exc


class EnvironmentVariableDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, environment_id, variable_id):
        variable = _get_member_variable(request.user, environment_id, variable_id)
        if not services.can_manage_environment(request.user, variable.environment, "environment.manage"):
            return _forbidden()
        services.delete_variable(variable=variable, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EnvironmentSecretListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.read"):
            return _forbidden()
        return Response(EnvironmentSecretSerializer(environment.secrets.all(), many=True).data)

    def post(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.secrets.manage"):
            return _forbidden()
        serializer = EnvironmentSecretWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if environment.secrets.filter(key=serializer.validated_data["key"]).exists():
            return Response(
                {"detail": "A secret with this key already exists in this environment. Rotate it instead."},
                status=status.HTTP_409_CONFLICT,
            )
        secret = services.create_secret(
            environment=environment,
            key=serializer.validated_data["key"],
            value=serializer.validated_data["value"],
            actor=request.user,
        )
        data = EnvironmentSecretSerializer(secret).data
        data["value"] = serializer.validated_data["value"]  # shown exactly once
        return Response(data, status=status.HTTP_201_CREATED)


def _get_member_secret(user, environment_id, secret_id) -> EnvironmentSecret:
    environment = services.get_member_environment(user, environment_id)
    try:
        return environment.secrets.get(id=secret_id)
    except EnvironmentSecret.DoesNotExist as exc:
        raise Http404 from exc


class EnvironmentSecretRotateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, environment_id, secret_id):
        secret = _get_member_secret(request.user, environment_id, secret_id)
        if not services.can_manage_environment(
            request.user, secret.environment, "environment.secrets.manage"
        ):
            return _forbidden()
        serializer = EnvironmentSecretWriteSerializer(data={**request.data, "key": secret.key})
        serializer.is_valid(raise_exception=True)
        secret = services.rotate_secret(
            secret=secret, value=serializer.validated_data["value"], actor=request.user
        )
        data = EnvironmentSecretSerializer(secret).data
        data["value"] = serializer.validated_data["value"]
        return Response(data, status=status.HTTP_201_CREATED)


class EnvironmentSecretDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, environment_id, secret_id):
        secret = _get_member_secret(request.user, environment_id, secret_id)
        if not services.can_manage_environment(
            request.user, secret.environment, "environment.secrets.manage"
        ):
            return _forbidden()
        services.delete_secret(secret=secret, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EnvironmentWebhookListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.read"):
            return _forbidden()
        return Response(EnvironmentWebhookSerializer(environment.webhooks.all(), many=True).data)

    def post(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        serializer = EnvironmentWebhookCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        webhook, signing_secret = services.create_webhook(
            environment=environment, actor=request.user, **serializer.validated_data
        )
        data = EnvironmentWebhookSerializer(webhook).data
        data["signing_secret"] = signing_secret  # shown exactly once
        return Response(data, status=status.HTTP_201_CREATED)


def _get_member_webhook(user, environment_id, webhook_id) -> EnvironmentWebhook:
    environment = services.get_member_environment(user, environment_id)
    try:
        return environment.webhooks.get(id=webhook_id)
    except EnvironmentWebhook.DoesNotExist as exc:
        raise Http404 from exc


class EnvironmentWebhookDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, environment_id, webhook_id):
        webhook = _get_member_webhook(request.user, environment_id, webhook_id)
        if not services.can_manage_environment(request.user, webhook.environment, "environment.manage"):
            return _forbidden()
        serializer = EnvironmentWebhookUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        webhook = services.update_webhook(webhook=webhook, actor=request.user, **serializer.validated_data)
        return Response(EnvironmentWebhookSerializer(webhook).data)

    def delete(self, request, environment_id, webhook_id):
        webhook = _get_member_webhook(request.user, environment_id, webhook_id)
        if not services.can_manage_environment(request.user, webhook.environment, "environment.manage"):
            return _forbidden()
        services.delete_webhook(webhook=webhook, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EnvironmentDatabaseBindingView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        serializer = DatabaseBindingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant_database_id = serializer.validated_data["tenant_database_id"]

        if tenant_database_id is None:
            services.unbind_database(environment=environment, actor=request.user)
            return Response(EnvironmentSerializer(environment).data)

        try:
            tenant_database = TenantDatabase.objects.select_related("project__workspace").get(
                id=tenant_database_id,
                project__workspace__organization_id=environment.organization_id,
            )
        except TenantDatabase.DoesNotExist as exc:
            raise Http404 from exc

        if tenant_database.environment_id and tenant_database.environment_id != environment.id:
            return Response(
                {"detail": "This database is already bound to a different environment."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            services.bind_database(
                environment=environment, tenant_database=tenant_database, actor=request.user
            )
        except IntegrityError:
            return Response(
                {"detail": "This environment already has a bound database."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(EnvironmentSerializer(environment).data)


class EnvironmentStorageBindingView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.manage"):
            return _forbidden()
        serializer = StorageBindingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bucket_id = serializer.validated_data["bucket_id"]

        if bucket_id is None:
            services.unbind_storage(environment=environment, actor=request.user)
            return Response(EnvironmentSerializer(environment).data)

        try:
            bucket = Bucket.objects.select_related("project__workspace").get(
                id=bucket_id,
                project__workspace__organization_id=environment.organization_id,
            )
        except Bucket.DoesNotExist as exc:
            raise Http404 from exc

        if bucket.environment_id and bucket.environment_id != environment.id:
            return Response(
                {"detail": "This bucket is already bound to a different environment."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            services.bind_storage(environment=environment, bucket=bucket, actor=request.user)
        except IntegrityError:
            return Response(
                {"detail": "This environment already has a bound bucket."}, status=status.HTTP_409_CONFLICT
            )
        return Response(EnvironmentSerializer(environment).data)


class EnvironmentCredentialListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.read"):
            return _forbidden()
        credentials = environment.credentials.all()
        return Response(ApplicationCredentialSerializer(credentials, many=True).data)

    def post(self, request, environment_id):
        environment = services.get_member_environment(request.user, environment_id)
        if not services.can_manage_environment(request.user, environment, "environment.secrets.manage"):
            return _forbidden()
        serializer = EnvironmentCredentialIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential, token = services.issue_environment_credential(
            environment=environment, actor=request.user, expires_at=serializer.validated_data["expires_at"]
        )
        data = ApplicationCredentialSerializer(credential).data
        data["secret"] = token  # shown exactly once
        return Response(data, status=status.HTTP_201_CREATED)


def _get_member_environment_credential(user, environment_id, credential_id) -> ApplicationCredential:
    environment = services.get_member_environment(user, environment_id)
    try:
        return environment.credentials.get(id=credential_id)
    except ApplicationCredential.DoesNotExist as exc:
        raise Http404 from exc


class EnvironmentCredentialRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, environment_id, credential_id):
        credential = _get_member_environment_credential(request.user, environment_id, credential_id)
        if not services.can_manage_environment(
            request.user, credential.environment, "environment.secrets.manage"
        ):
            return _forbidden()
        services.revoke_environment_credential(credential=credential, actor=request.user)
        return Response(ApplicationCredentialSerializer(credential).data)


class EnvironmentCredentialRotateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, environment_id, credential_id):
        credential = _get_member_environment_credential(request.user, environment_id, credential_id)
        if not services.can_manage_environment(
            request.user, credential.environment, "environment.secrets.manage"
        ):
            return _forbidden()
        new_credential, token = services.rotate_environment_credential(
            credential=credential, actor=request.user
        )
        data = ApplicationCredentialSerializer(new_credential).data
        data["secret"] = token
        return Response(data, status=status.HTTP_201_CREATED)
