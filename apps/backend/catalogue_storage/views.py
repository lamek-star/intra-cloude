from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.models import ApplicationCredential
from audit import services as audit
from audit.models import AuditEvent
from storage.backends import get_client

from . import services
from .models import Diagram, OEMPart
from .serializers import OEMPartSerializer


class OEMPartSearchView(APIView):
    """`GET /api/v1/catalogue/oem-parts/?q=<part number, any format>` —
    the one search this integration needs: exact match on the
    normalized part number (see services.search_part). Reachable by
    either a human session or this deployment's spare-parts
    ApplicationCredential — reference catalogue data, not sensitive."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get("q", "")
        part = services.search_part(query)
        if part is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(OEMPartSerializer(part).data)


class OEMPartImportView(APIView):
    """`POST /api/v1/catalogue/oem-parts/import/` — lets an external,
    bearer-authenticated caller (the spare-parts backend, resolving a
    live provider lookup on a cache miss) persist exactly one part+
    diagram+link, through the identical idempotent path the CSV importer
    and seed migration both use (services.import_row) — never a bulk
    operation, one record per call. Metadata only: this never accepts
    image bytes, so it can never be used to smuggle local image storage
    around the CSV importer's own --license-confirmed gate.

    This shared reference catalogue has no organization owner to gate
    writes with a capability check (see docs/CATALOGUE_STORAGE.md
    "Access model") — instead the gate is authentication *shape*, the
    same pattern environments.services.check_environment_scope uses:
    only a request authenticated via an `ApplicationCredential` bearer
    token (`request.auth`) may write here. A plain human session — any
    registered user, not just this integration's own operators — is
    refused, matching the seed migration's intent that only the
    dedicated "Harmoney Spare Parts — Catalogue Storage" Application (or
    another explicitly issued bearer credential) can mutate the shared
    catalogue."""

    permission_classes = [IsAuthenticated]

    REQUIRED_FIELDS = ("part_number", "manufacturer", "provider", "provider_diagram_id")

    def post(self, request):
        if not isinstance(request.auth, ApplicationCredential):
            audit.record(
                actor=request.user,
                organization_id=None,
                action="catalogue.oem_part.import",
                result=AuditEvent.Result.DENIED,
                context={"reason": "not bearer-token authenticated"},
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        body = request.data
        missing = [f for f in self.REQUIRED_FIELDS if not body.get(f)]
        if missing:
            return Response(
                {"detail": f"Missing required field(s): {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        row = services.ImportRow(
            part_number=body["part_number"],
            description=body.get("description", ""),
            manufacturer=body["manufacturer"],
            diagram_code=body.get("diagram_code", ""),
            provider=body["provider"],
            provider_diagram_id=body["provider_diagram_id"],
            callout=body.get("callout", ""),
            source_image_url=body.get("source_image_url", ""),
            applicability=body.get("applicability", ""),
            fitment_notes=body.get("fitment_notes", ""),
            x=body.get("x"), y=body.get("y"), width=body.get("width"), height=body.get("height"),
        )
        result = services.ImportResult()
        services.import_row(row, result)
        part = OEMPart.objects.get(normalized_part_number=services.normalize_part_number(row.part_number))
        audit.record(
            actor=request.user,
            organization_id=None,
            action="catalogue.oem_part.import",
            resource_type="oem_part",
            resource_id=part.id,
        )
        return Response(OEMPartSerializer(part).data, status=status.HTTP_201_CREATED)


class OEMPartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, part_id):
        part = OEMPart.objects.filter(pk=part_id).first()
        if part is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(OEMPartSerializer(part).data)


class DiagramImageView(APIView):
    """`GET /api/v1/catalogue/diagrams/{id}/image/` — only ever serves a
    LOCALLY_STORED diagram's actual bytes (streamed through the backend,
    same reasoning as storage.views.FileDownloadView: the object storage
    endpoint is an internal Docker DNS name). An EXTERNAL_REFERENCE_ONLY
    diagram has no `file` and always 404s here — callers use
    `source_image_url` for attribution, never fetch it through this
    endpoint."""

    permission_classes = [IsAuthenticated]

    def get(self, request, diagram_id):
        diagram = Diagram.objects.filter(pk=diagram_id).first()
        if diagram is None or diagram.license_status != Diagram.LicenseStatus.LOCALLY_STORED or not diagram.file_id:
            return Response(status=status.HTTP_404_NOT_FOUND)
        file_obj = diagram.file
        body = get_client().get_stream(file_obj.object_key)
        response = StreamingHttpResponse(body.iter_chunks(1024 * 1024), content_type=file_obj.mime_type)
        response["Content-Length"] = str(file_obj.size)
        return response
