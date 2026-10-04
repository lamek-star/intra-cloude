from rest_framework import serializers

from .models import Diagram, DiagramPart, OEMPart


class DiagramSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Diagram
        fields = [
            "id", "provider", "provider_diagram_id", "diagram_code",
            "license_status", "source_image_url", "image_url",
        ]

    def get_image_url(self, diagram: Diagram):
        # Only a locally-stored, permission-confirmed image gets a
        # downloadable URL from this app; EXTERNAL_REFERENCE_ONLY always
        # returns null here -- the caller falls back to source_image_url
        # for attribution/display-elsewhere-with-permission decisions,
        # never to an image this app serves itself.
        if diagram.license_status != Diagram.LicenseStatus.LOCALLY_STORED or not diagram.file_id:
            return None
        return f"/api/v1/catalogue/diagrams/{diagram.id}/image/"


class DiagramPartSerializer(serializers.ModelSerializer):
    diagram = DiagramSerializer()

    class Meta:
        model = DiagramPart
        fields = ["callout", "x", "y", "width", "height", "diagram"]


class OEMPartSerializer(serializers.ModelSerializer):
    diagram_parts = DiagramPartSerializer(many=True, read_only=True)

    class Meta:
        model = OEMPart
        fields = [
            "id", "manufacturer", "part_number", "normalized_part_number",
            "description", "applicability", "fitment_notes", "diagram_parts",
        ]
