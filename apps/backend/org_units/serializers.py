from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import OrganizationalUnit, UnitMembership


class OrganizationalUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationalUnit
        fields = ["id", "organization", "parent", "unit_type", "name", "created_at", "created_by"]
        read_only_fields = fields


class OrganizationalUnitTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationalUnit
        fields = ["id", "unit_type", "name", "children"]
        read_only_fields = fields

    def get_children(self, obj):
        return OrganizationalUnitTreeSerializer(obj.children.all(), many=True).data


class UnitParentInput(serializers.Serializer):
    def get_fields(self):
        fields = super().get_fields()
        # Serializer.parent is an internal binding attribute. Keep the wire
        # field named parent without shadowing that attribute on the class.
        fields["parent"] = serializers.UUIDField(required=False, allow_null=True)
        return fields


class OrganizationalUnitCreateSerializer(UnitParentInput):
    name = serializers.CharField(max_length=200)
    unit_type = serializers.CharField(max_length=100)


class OrganizationalUnitUpdateSerializer(UnitParentInput):
    name = serializers.CharField(max_length=200, required=False)
    unit_type = serializers.CharField(max_length=100, required=False)


class UnitMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UnitMembership
        fields = ["id", "unit", "user", "created_at"]
        read_only_fields = fields


class UnitMemberAddSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
