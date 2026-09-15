from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from applications import services as app_services
from audit.models import AuditEvent
from catalogue_storage import services
from catalogue_storage.models import Diagram, DiagramPart, OEMPart
from organizations.models import Organization


def _bare_organization(name: str, owner) -> Organization:
    """A minimal Organization with no role assignment -- register_application
    only needs something to own the Application on, and going through the
    real organizations.services.create_organization would require the
    permission catalog to already be seeded (assign_role's own
    "organization-administrator" lookup), which these tests have no other
    reason to depend on. Same reasoning as
    catalogue_storage/migrations/0002_seed_spare_parts_catalogue.py's own
    seed function."""
    return Organization.objects.create(name=name, slug=name.lower().replace(" ", "-"), created_by=owner)


class NormalizationTests(APITestCase):
    def test_dash_space_and_case_are_all_normalized_the_same_way(self):
        self.assertEqual(services.normalize_part_number("15690-65010"), "1569065010")
        self.assertEqual(services.normalize_part_number("1569065010"), "1569065010")
        self.assertEqual(services.normalize_part_number("15690 65010"), "1569065010")
        self.assertEqual(services.normalize_part_number("15690-65010"), services.normalize_part_number("15690 65010"))

    def test_part_number_display_format_is_preserved_separately(self):
        part = OEMPart.objects.create(manufacturer="Toyota", part_number="TEST-00001")
        self.assertEqual(part.part_number, "TEST-00001")
        self.assertEqual(part.normalized_part_number, "TEST00001")


class ImportRowTests(APITestCase):
    """Uses synthetic TEST-* identifiers throughout, deliberately distinct
    from the real 15690-65010/MAB896 sample the seed migration
    (0002_seed_spare_parts_catalogue) already loads into every database
    including the test one -- these tests exercise the import mechanism
    generically, not that one specific record (see SearchAPITests below
    for coverage against the real seeded sample)."""

    def _row(self, **overrides):
        defaults = dict(
            part_number="TEST-00001", description="Test Part One",
            manufacturer="Toyota", diagram_code="TESTDIAG1", provider="test-provider",
            provider_diagram_id="TESTDIAG1", callout="00001",
            source_image_url="https://example.com/TESTDIAG1.png",
            x=536, y=672, width=66, height=20,
        )
        defaults.update(overrides)
        return services.ImportRow(**defaults)

    def test_import_creates_part_diagram_and_link(self):
        result = services.ImportResult()
        services.import_row(self._row(), result)
        self.assertEqual(result.parts_created, 1)
        self.assertEqual(result.diagrams_created, 1)
        self.assertEqual(result.links_created, 1)
        part = OEMPart.objects.get(normalized_part_number="TEST00001")
        self.assertEqual(part.description, "Test Part One")
        diagram = Diagram.objects.get(provider="test-provider", provider_diagram_id="TESTDIAG1")
        self.assertEqual(diagram.license_status, Diagram.LicenseStatus.EXTERNAL_REFERENCE_ONLY)
        link = DiagramPart.objects.get(diagram=diagram, part=part)
        self.assertEqual(link.callout, "00001")
        self.assertEqual((link.x, link.y, link.width, link.height), (536, 672, 66, 20))

    def test_reimporting_the_same_row_updates_in_place_not_duplicates(self):
        result = services.ImportResult()
        services.import_row(self._row(), result)
        services.import_row(self._row(description="Test Part One (rev)"), result)
        self.assertEqual(OEMPart.objects.filter(normalized_part_number="TEST00001").count(), 1)
        self.assertEqual(Diagram.objects.filter(provider="test-provider").count(), 1)
        self.assertEqual(DiagramPart.objects.filter(diagram__provider="test-provider").count(), 1)
        self.assertEqual(result.parts_created, 1)
        self.assertEqual(result.parts_updated, 1)
        self.assertEqual(
            OEMPart.objects.get(normalized_part_number="TEST00001").description, "Test Part One (rev)"
        )

    def test_multiple_parts_share_one_diagram_without_duplicating_it(self):
        result = services.ImportResult()
        services.import_row(self._row(), result)
        services.import_row(
            self._row(part_number="TEST-00002", description="Other part on same diagram", callout="00002"),
            result,
        )
        self.assertEqual(
            Diagram.objects.filter(provider="test-provider").count(), 1,
            "the second row must reuse the existing diagram",
        )
        self.assertEqual(result.diagrams_created, 1)
        self.assertEqual(result.diagrams_reused, 1)
        diagram = Diagram.objects.get(provider="test-provider", provider_diagram_id="TESTDIAG1")
        self.assertEqual(diagram.diagram_parts.count(), 2)

    def test_one_part_can_appear_on_more_than_one_diagram(self):
        result = services.ImportResult()
        services.import_row(self._row(), result)
        services.import_row(
            self._row(diagram_code="TESTDIAG2", provider_diagram_id="TESTDIAG2", callout="99999"), result
        )
        part = OEMPart.objects.get(normalized_part_number="TEST00001")
        self.assertEqual(part.diagram_parts.count(), 2)

    def test_missing_hotspot_coordinates_are_left_null_not_fabricated(self):
        result = services.ImportResult()
        services.import_row(self._row(x=None, y=None, width=None, height=None), result)
        link = DiagramPart.objects.get(diagram__provider="test-provider")
        self.assertIsNone(link.x)
        self.assertIsNone(link.y)


class SearchAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="reader@example.com", password="x")
        self.client.force_login(self.user)
        result = services.ImportResult()
        services.import_row(
            services.ImportRow(
                part_number="15690-65010", description="VALVE ASSY, OIL COOLER RELIEF",
                manufacturer="Toyota", diagram_code="MAB896", provider="toyota-epc",
                provider_diagram_id="MAB896", callout="15690",
                source_image_url="https://toyota-epc.aftermarketcatalog.com/image/figure/EU/A2/MAB896.png",
                x=536, y=672, width=66, height=20,
            ),
            result,
        )

    def test_search_by_official_display_format(self):
        response = self.client.get(reverse("oem-part-search"), {"q": "15690-65010"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["part_number"], "15690-65010")

    def test_search_by_normalized_format(self):
        response = self.client.get(reverse("oem-part-search"), {"q": "1569065010"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["normalized_part_number"], "1569065010")

    def test_search_by_space_separated_format(self):
        response = self.client.get(reverse("oem-part-search"), {"q": "15690 65010"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["part_number"], "15690-65010")

    def test_all_three_formats_return_the_identical_part(self):
        ids = {
            self.client.get(reverse("oem-part-search"), {"q": q}).data["id"]
            for q in ("15690-65010", "1569065010", "15690 65010")
        }
        self.assertEqual(len(ids), 1)

    def test_unknown_part_number_is_a_clean_404(self):
        response = self.client.get(reverse("oem-part-search"), {"q": "00000-00000"})
        self.assertEqual(response.status_code, 404)

    def test_result_includes_diagram_and_callout_but_no_image_url_when_external_reference_only(self):
        response = self.client.get(reverse("oem-part-search"), {"q": "15690-65010"})
        diagram_part = response.data["diagram_parts"][0]
        self.assertEqual(diagram_part["callout"], "15690")
        self.assertEqual(diagram_part["diagram"]["license_status"], "EXTERNAL_REFERENCE_ONLY")
        self.assertIsNone(diagram_part["diagram"]["image_url"])
        self.assertTrue(diagram_part["diagram"]["source_image_url"].startswith("https://"))

    def test_anonymous_request_is_denied(self):
        self.client.logout()
        response = self.client.get(reverse("oem-part-search"), {"q": "15690-65010"})
        self.assertEqual(response.status_code, 403)

    def test_diagram_image_endpoint_404s_for_an_external_reference_only_diagram(self):
        diagram = Diagram.objects.get()
        response = self.client.get(reverse("diagram-image", args=[diagram.id]))
        self.assertEqual(response.status_code, 404)

    def test_search_falls_back_to_a_description_match_when_no_number_matches(self):
        response = self.client.get(reverse("oem-part-search"), {"q": "OIL COOLER RELIEF"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["part_number"], "15690-65010")

    def test_applicability_and_fitment_notes_round_trip(self):
        response = self.client.get(reverse("oem-part-search"), {"q": "15690-65010"})
        self.assertIn("applicability", response.data)
        self.assertIn("fitment_notes", response.data)


class ImportEndpointTests(APITestCase):
    """Write access is gated on authentication *shape*, not a capability
    (this catalogue has no organization owner to check one against) --
    only a bearer-token-authenticated (`ApplicationCredential`) caller may
    import; a plain human session, however legitimate its login, may not.
    See OEMPartImportView's own docstring."""

    def setUp(self):
        cache.clear()
        owner = User.objects.create_user(email="catalogue-owner@example.com", password="x")
        org = _bare_organization("Catalogue Integration Org", owner)
        application = app_services.register_application(
            organization=org, name="Catalogue Importer Bot", description="", owner=owner
        )
        _, token = app_services.issue_credential(service_account=application.service_account, actor=owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _payload(self, **overrides):
        defaults = dict(
            part_number="TEST-99001", description="Test Import Part", manufacturer="Toyota",
            diagram_code="TESTDIAG9", provider="test-provider", provider_diagram_id="TESTDIAG9",
            callout="99001", applicability="Production 2020-01-current",
        )
        defaults.update(overrides)
        return defaults

    def test_import_creates_a_searchable_part(self):
        response = self.client.post(reverse("oem-part-import"), self._payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["applicability"], "Production 2020-01-current")

        found = self.client.get(reverse("oem-part-search"), {"q": "TEST-99001"})
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.data["part_number"], "TEST-99001")

    def test_import_is_idempotent(self):
        self.client.post(reverse("oem-part-import"), self._payload(), format="json")
        self.client.post(reverse("oem-part-import"), self._payload(description="Updated"), format="json")
        self.assertEqual(OEMPart.objects.filter(normalized_part_number="TEST99001").count(), 1)
        self.assertEqual(OEMPart.objects.get(normalized_part_number="TEST99001").description, "Updated")

    def test_import_rejects_a_payload_missing_required_fields(self):
        response = self.client.post(reverse("oem-part-import"), {"description": "no part number"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_import_never_creates_a_locally_stored_diagram(self):
        self.client.post(reverse("oem-part-import"), self._payload(), format="json")
        diagram = Diagram.objects.get(provider="test-provider", provider_diagram_id="TESTDIAG9")
        self.assertEqual(diagram.license_status, Diagram.LicenseStatus.EXTERNAL_REFERENCE_ONLY)
        self.assertIsNone(diagram.file_id)

    def test_import_records_an_audit_event(self):
        response = self.client.post(reverse("oem-part-import"), self._payload(), format="json")
        part_id = response.data["id"]
        event = AuditEvent.objects.get(action="catalogue.oem_part.import", resource_id=str(part_id))
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)

    def test_a_plain_human_session_cannot_import_even_if_logged_in(self):
        self.client.credentials()  # drop the bearer token set up in setUp
        human = User.objects.create_user(email="just-a-user@example.com", password="x")
        self.client.force_login(human)
        response = self.client.post(reverse("oem-part-import"), self._payload(), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(OEMPart.objects.filter(normalized_part_number="TEST99001").exists())
        event = AuditEvent.objects.get(action="catalogue.oem_part.import")
        self.assertEqual(event.result, AuditEvent.Result.DENIED)

    def test_another_integrations_bearer_credential_can_still_import(self):
        """Write access is gated on being bearer-authenticated at all, not
        on being this one specific seeded Application -- any Application
        an operator has deliberately issued a credential for may write,
        matching "explicitly issued bearer credential" in the view's own
        docstring."""
        other_owner = User.objects.create_user(email="other-owner@example.com", password="x")
        other_org = _bare_organization("Some Other Org", other_owner)
        other_app = app_services.register_application(
            organization=other_org, name="Unrelated Integration", description="", owner=other_owner
        )
        _, other_token = app_services.issue_credential(
            service_account=other_app.service_account, actor=other_owner
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_token}")
        response = self.client.post(reverse("oem-part-import"), self._payload(), format="json")
        self.assertEqual(response.status_code, 201)
