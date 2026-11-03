from django.http import Http404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.services import get_member_organization
from permissions.services import has_permission

from . import internet, services
from .models import InternetGateway, Site, SiteVersion
from .serializers import (
    SiteCreateSerializer,
    SiteDetailSerializer,
    SiteSerializer,
    SiteUpdateSerializer,
    SiteVersionSerializer,
    SiteVersionUploadSerializer,
)


def _forbidden():
    return Response(status=status.HTTP_403_FORBIDDEN)


def _bad_request(exc: Exception):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def get_member_site(user, site_id) -> Site:
    """A site only if the requester is an active member of its organization; otherwise 404, so another
    organization's sites are not revealed (THREAT_MODEL.md Section 4)."""
    site = Site.objects.select_related("active_version").filter(id=site_id).first()
    if site is None:
        raise Http404
    get_member_organization(user, site.organization_id)
    return site


def _can(user, code: str, site: Site) -> bool:
    return has_permission(user, code, organization_id=site.organization_id, resource=("site", str(site.id)))


class SiteListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, organization_id):
        organization = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "sites.read", organization_id=organization.id):
            return _forbidden()
        sites = Site.objects.filter(organization=organization).select_related("active_version__uploaded_by")
        return Response(SiteSerializer(sites, many=True).data)

    def post(self, request, organization_id):
        organization = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "sites.manage", organization_id=organization.id):
            return _forbidden()
        serializer = SiteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            site = services.create_site(
                organization=organization,
                name=data["name"],
                slug=data["slug"],
                upload=data["file"],
                single_page_app=data["single_page_app"],
                actor=request.user,
            )
        except services.SiteError as exc:
            return _bad_request(exc)
        return Response(SiteDetailSerializer(site).data, status=status.HTTP_201_CREATED)


class SiteDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request, site_id):
        site = get_member_site(request.user, site_id)
        if not _can(request.user, "sites.read", site):
            return _forbidden()
        services.refresh_runtime(site)
        return Response(SiteDetailSerializer(site).data)

    def patch(self, request, site_id):
        site = get_member_site(request.user, site_id)
        if not _can(request.user, "sites.manage", site):
            return _forbidden()
        serializer = SiteUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        fields = dict(serializer.validated_data)
        hostname = fields.pop("hostname", None)
        try:
            if hostname is not None:
                services.set_hostname(site=site, hostname=hostname, actor=request.user)
            services.update_site(site=site, actor=request.user, **fields)
        except services.SiteError as exc:
            return _bad_request(exc)
        return Response(SiteDetailSerializer(site).data)

    def delete(self, request, site_id):
        site = get_member_site(request.user, site_id)
        if not _can(request.user, "sites.manage", site):
            return _forbidden()
        services.delete_site(site=site, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteVersionListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, site_id):
        site = get_member_site(request.user, site_id)
        if not _can(request.user, "sites.read", site):
            return _forbidden()
        return Response(SiteVersionSerializer(site.versions.select_related("uploaded_by"), many=True).data)

    def post(self, request, site_id):
        site = get_member_site(request.user, site_id)
        if not _can(request.user, "sites.manage", site):
            return _forbidden()
        serializer = SiteVersionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = services.upload_version(
                site=site,
                upload=serializer.validated_data["file"],
                activate=serializer.validated_data["activate"],
                actor=request.user,
            )
        except services.SiteError as exc:
            return _bad_request(exc)
        return Response(SiteVersionSerializer(version).data, status=status.HTTP_201_CREATED)


def _get_version(site: Site, version_id) -> SiteVersion:
    version = site.versions.filter(id=version_id).first()
    if version is None:
        raise Http404
    return version


class SiteVersionActivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, site_id, version_id):
        site = get_member_site(request.user, site_id)
        if not _can(request.user, "sites.manage", site):
            return _forbidden()
        version = _get_version(site, version_id)
        services.activate_version(site=site, version=version, actor=request.user)
        return Response(SiteDetailSerializer(site).data)


class SiteVersionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, site_id, version_id):
        site = get_member_site(request.user, site_id)
        if not _can(request.user, "sites.manage", site):
            return _forbidden()
        version = _get_version(site, version_id)
        try:
            services.delete_version(site=site, version=version, actor=request.user)
        except services.SiteError as exc:
            return _bad_request(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- the internet gate (ADR-0020 decision 4)


class InternetGatewayView(APIView):
    """The gate's state. Everyone signed in may see whether it is on; only the Super Administrator sees the
    tunnel and what is published."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not internet.can_manage(request.user):
            return Response({"enabled": InternetGateway.current().enabled, "can_manage": False})
        return Response({**internet.status(), "can_manage": True})


class InternetGatewayEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        try:
            result = internet.enable(
                actor=request.user,
                token=str(data.get("token") or ""),
                password=str(data.get("password") or ""),
            )
        except PermissionError:
            return _forbidden()
        except services.SiteError as exc:
            return _bad_request(exc)
        return Response({**result, "can_manage": True})


class InternetGatewayDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            result = internet.disable(actor=request.user)
        except PermissionError:
            return _forbidden()
        except services.SiteError as exc:
            return _bad_request(exc)
        return Response({**result, "can_manage": True})


class SiteInternetView(APIView):
    """Publish a site under a public name, or revoke it. The Super Administrator acts platform-wide, so the
    site is looked up directly -- but only for them; anyone else is refused before any lookup."""

    permission_classes = [IsAuthenticated]

    def _site(self, request, site_id):
        if not internet.can_manage(request.user):
            raise PermissionError
        site = Site.objects.filter(id=site_id).first()
        if site is None:
            raise Http404
        return site

    def post(self, request, site_id):
        try:
            site = self._site(request, site_id)
            internet.publish(actor=request.user, site=site, hostname=str(request.data.get("hostname") or ""))
        except PermissionError:
            return _forbidden()
        except services.SiteError as exc:
            return _bad_request(exc)
        return Response(SiteDetailSerializer(site).data)

    def delete(self, request, site_id):
        try:
            site = self._site(request, site_id)
            internet.revoke(actor=request.user, site=site)
        except PermissionError:
            return _forbidden()
        except services.SiteError as exc:
            return _bad_request(exc)
        return Response(SiteDetailSerializer(site).data)
