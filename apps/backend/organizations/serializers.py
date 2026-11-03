from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import Membership, Organization, Team
from .services import service_account_of


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "external_sharing_enabled", "created_at", "created_by"]
        read_only_fields = fields


class OrganizationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    # Set when this member is an Application's service account (applications.ServiceAccount): the
    # members page shows it as that application, without the role picker -- a service account gets
    # access through resource grants, never an organization role (PERMISSIONS.md section 3).
    application = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["id", "user", "organization", "team", "status", "created_at", "application"]
        read_only_fields = fields

    def get_application(self, membership: Membership) -> dict | None:
        account = service_account_of(membership.user)
        if account is None:
            return None
        return {"id": str(account.application_id), "name": account.application.name}


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()


class AssignRoleSerializer(serializers.Serializer):
    role_slug = serializers.CharField(max_length=100)


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "organization", "name", "created_at"]
        read_only_fields = fields


class TeamCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)


class TeamMemberSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
