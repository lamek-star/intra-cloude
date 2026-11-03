from django.conf import settings
from rest_framework import serializers

from .models import Site, SiteVersion


class SiteVersionSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.SerializerMethodField()

    class Meta:
        model = SiteVersion
        fields = [
            "id",
            "number",
            "original_filename",
            "manifest",
            "file_count",
            "total_bytes",
            "notes",
            "uploaded_by_email",
            "created_at",
        ]

    def get_uploaded_by_email(self, obj) -> str:
        return obj.uploaded_by.email if obj.uploaded_by else ""


class SiteSerializer(serializers.ModelSerializer):
    active_version = SiteVersionSerializer(read_only=True)
    path = serializers.SerializerMethodField()
    public_port = serializers.SerializerMethodField()
    lan_address = serializers.SerializerMethodField()

    class Meta:
        model = Site
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "status",
            "single_page_app",
            "hostname",
            "internet_hostname",
            "lan_address",
            "kind",
            "runtime_state",
            "runtime_log",
            "application",
            "active_version",
            "path",
            "public_port",
            "created_at",
            "updated_at",
        ]

    def get_path(self, obj) -> str:
        return f"/{obj.slug}/"

    def get_lan_address(self, obj) -> str:
        # Where the site's own name must point on the other PCs (hosts file / router DNS); empty = this
        # PC only.
        return settings.SITES_LAN_ADDRESS

    def get_public_port(self, obj) -> int:
        # The browser builds the address from the host it already uses for IntraForge plus this port.
        return settings.SITES_PUBLIC_PORT


class SiteDetailSerializer(SiteSerializer):
    versions = SiteVersionSerializer(many=True, read_only=True)

    class Meta(SiteSerializer.Meta):
        fields = [*SiteSerializer.Meta.fields, "versions"]


class SiteCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    slug = serializers.CharField(max_length=50)
    single_page_app = serializers.BooleanField(required=False, default=False)
    file = serializers.FileField()


class SiteUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    status = serializers.ChoiceField(choices=Site.Status.choices, required=False)
    single_page_app = serializers.BooleanField(required=False)
    # Its own name on the shop network; "" removes it.
    hostname = serializers.CharField(max_length=253, required=False, allow_blank=True)


class SiteVersionUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    activate = serializers.BooleanField(required=False, default=True)
