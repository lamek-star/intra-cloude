from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import Membership, Organization, Team


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "external_sharing_enabled", "created_at", "created_by"]
        read_only_fields = fields


class OrganizationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "organization", "team", "status", "created_at"]
        read_only_fields = fields


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
