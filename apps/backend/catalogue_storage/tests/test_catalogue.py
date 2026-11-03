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
        self.assertEqual(
            services.normalize_part_number("15690-65010"), services.normalize_part_number("15690 65010")
        )

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
        defaults = {
            "part_number": "TEST-00001", "description": "Test Part One",
            "manufacturer": "Toyota", "diagram_code": "TESTDIAG1", "provider": "test-provider",
            "provider_diagram_id": "TESTDIAG1", "callout": "00001",
            "source_image_url": "https://example.com/TESTDIAG1.png",
            "x": 536, "y": 672, "width": 66, "height": 20,
        }
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
        defaults = {
            "part_number": "TEST-99001", "description": "Test Import Part", "manufacturer": "Toyota",
            "diagram_code": "TESTDIAG9", "provider": "test-provider", "provider_diagram_id": "TESTDIAG9",
            "callout": "99001", "applicability": "Production 2020-01-current",
        }
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
        response = self.client.post(
            reverse("oem-part-import"), {"description": "no part number"}, format="json"
        )
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


class FigureImportTests(APITestCase):
    """A figure import stores the whole parts list of one figure so every
    number on it is listed offline and independently searchable."""

    def setUp(self):
        cache.clear()
        owner = User.objects.create_user(email="figure-owner@example.com", password="x")
        org = _bare_organization("Figure Integration Org", owner)
        application = app_services.register_application(
            organization=org, name="Figure Importer Bot", description="", owner=owner
        )
        _, token = app_services.issue_credential(service_account=application.service_account, actor=owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _figure(self):
        rect = {"x": 10, "y": 20, "width": 60, "height": 18}
        return {
            "hotspots": [{"label": "T1", "pnc": "T1", "resolved": True, "rect": rect}],
            "groups": [
                {
                    "callout": "T1", "pnc": "T1", "name": "Test Valve", "rect": rect,
                    "rows": [
                        {"part_number": "FIG-00001", "description": "Test Valve", "valid_from": "1988-08",
                         "valid_to": "1989-08", "is_current": False, "fitment": ["3VZE"],
                         "has_remarks": True},
                        {"part_number": "FIG-00001", "description": "Test Valve", "valid_from": "1989-08",
                         "valid_to": None, "is_current": True, "fitment": ["VZN85"], "has_remarks": False},
                        {"part_number": "FIG-00002", "description": "Test Valve Seal", "valid_from": None,
                         "valid_to": None, "is_current": True, "fitment": [], "has_remarks": False},
                    ],
                },
                {"callout": "T2", "pnc": "T2", "name": "Test Bolt", "rect": None,
                 "rows": [{"part_number": "FIG-00003", "description": "Test Bolt", "is_current": True,
                           "fitment": [], "has_remarks": False}]},
            ],
        }

    def _payload(self, **overrides):
        payload = {
            "provider": "test-provider", "provider_diagram_id": "FIGDIAG1", "diagram_code": "FIGDIAG1",
            "source_image_url": "https://example.com/FIGDIAG1.png", "manufacturer": "Toyota",
            "figure_data": self._figure(),
        }
        payload.update(overrides)
        return payload

    def test_every_distinct_number_becomes_a_searchable_part_linked_to_its_callout(self):
        response = self.client.post(reverse("diagram-figure-import"), self._payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["parts_created"], 3)  # the repeated FIG-00001 counts once
        for number in ("FIG-00001", "FIG-00002", "FIG-00003"):
            found = self.client.get(reverse("oem-part-search"), {"q": number})
            self.assertEqual(found.status_code, 200, number)
        seal = self.client.get(reverse("oem-part-search"), {"q": "FIG-00002"}).data
        self.assertEqual(seal["diagram_parts"][0]["callout"], "T1")
        self.assertEqual(seal["diagram_parts"][0]["width"], 60)
        self.assertTrue(seal["diagram_parts"][0]["diagram"]["has_figure"])
        bolt = self.client.get(reverse("oem-part-search"), {"q": "FIG-00003"}).data
        self.assertIsNone(bolt["diagram_parts"][0]["x"])  # no rect supplied -> none fabricated

    def test_diagram_detail_returns_the_full_snapshot_from_the_database(self):
        created = self.client.post(reverse("diagram-figure-import"), self._payload(), format="json")
        detail = self.client.get(reverse("diagram-detail", args=[created.data["id"]]))
        self.assertEqual(detail.status_code, 200)
        rows = [r for g in detail.data["figure_data"]["groups"] for r in g["rows"]]
        self.assertEqual(len(rows), 4)  # variants are kept as separate rows for display

    def test_reimport_is_idempotent(self):
        self.client.post(reverse("diagram-figure-import"), self._payload(), format="json")
        self.client.post(reverse("diagram-figure-import"), self._payload(), format="json")
        self.assertEqual(Diagram.objects.filter(provider="test-provider").count(), 1)
        self.assertEqual(OEMPart.objects.filter(normalized_part_number__startswith="FIG0000").count(), 3)

    def test_figure_import_never_creates_a_locally_stored_diagram(self):
        self.client.post(reverse("diagram-figure-import"), self._payload(), format="json")
        diagram = Diagram.objects.get(provider="test-provider", provider_diagram_id="FIGDIAG1")
        self.assertEqual(diagram.license_status, Diagram.LicenseStatus.EXTERNAL_REFERENCE_ONLY)
        self.assertIsNone(diagram.file_id)

    def test_malformed_figure_data_is_a_clean_400_and_writes_nothing(self):
        for bad in ({"groups": "nope"}, {"groups": [{"rows": [{"description": "no number"}]}]}):
            response = self.client.post(
                reverse("diagram-figure-import"), self._payload(figure_data=bad), format="json"
            )
            self.assertEqual(response.status_code, 400)
        self.assertFalse(Diagram.objects.filter(provider="test-provider").exists())

    def test_oversized_figure_is_refused(self):
        rows = [{"part_number": f"BIG-{i:05d}"} for i in range(services.MAX_FIGURE_ROWS + 1)]
        response = self.client.post(
            reverse("diagram-figure-import"),
            self._payload(figure_data={"groups": [{"callout": "X", "rows": rows}]}),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_a_plain_human_session_cannot_import_a_figure(self):
        self.client.credentials()
        self.client.force_login(User.objects.create_user(email="figure-human@example.com", password="x"))
        response = self.client.post(reverse("diagram-figure-import"), self._payload(), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Diagram.objects.filter(provider="test-provider").exists())

    def test_a_diagram_without_a_figure_reports_has_figure_false(self):
        self.client.post(reverse("oem-part-import"), {
            "part_number": "TEST-77001", "manufacturer": "Toyota", "provider": "test-provider",
            "provider_diagram_id": "PLAINDIAG",
        }, format="json")
        part = self.client.get(reverse("oem-part-search"), {"q": "TEST-77001"}).data
        self.assertFalse(part["diagram_parts"][0]["diagram"]["has_figure"])


class DiagramImageImportTests(APITestCase):
    """The drawings importer: gated behind --license-confirmed, matches files
    to Diagrams by figure key, stores bytes in real object storage."""

    PNG = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        b"\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7V\xbd\xfa\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def setUp(self):
        import tempfile
        from pathlib import Path

        # The seed migration creates the catalogue organization, but a reused test database
        # (--reuse-db) may have been flushed by an earlier TransactionTestCase run.
        if not Organization.objects.filter(name=services.CATALOGUE_ORG_NAME).exists():
            owner = User.objects.create_user(email="catalogue-owner@example.com", password="x")
            _bare_organization(services.CATALOGUE_ORG_NAME, owner)

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "pageA_files").mkdir()
        (self.root / "pageB_files").mkdir()
        (self.root / "pageA_files" / "IMG1.png").write_bytes(self.PNG)
        (self.root / "pageB_files" / "IMG1.png").write_bytes(self.PNG)  # same figure saved from another page
        (self.root / "pageB_files" / "IMG2.png").write_bytes(self.PNG)
        (self.root / "pageB_files" / "notes.txt").write_text("not an image")
        (self.root / "pageB_files" / "FAKE.png").write_bytes(b"<html>not really a png</html>")

    def _run(self, *args):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command(
            "import_diagram_images", "--dir", str(self.root), "--provider", "test-provider", *args, stdout=out
        )
        return out.getvalue()

    def test_refuses_without_license_confirmation_and_writes_nothing(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self._run()
        self.assertFalse(Diagram.objects.filter(provider="test-provider").exists())

    def test_dry_run_reports_but_writes_nothing(self):
        output = self._run("--license-confirmed", "--dry-run")
        self.assertIn("DRY RUN", output)
        self.assertIn("drawings attached:   2", output)
        self.assertFalse(Diagram.objects.filter(provider="test-provider").exists())

    def test_attaches_each_figure_once_and_skips_non_images(self):
        output = self._run("--license-confirmed")
        self.assertIn("drawings attached:   2", output)
        self.assertIn("duplicate file names: 1", output)
        self.assertIn("FAKE.png: not a PNG/JPEG file", output)
        for key in ("IMG1", "IMG2"):
            diagram = Diagram.objects.get(provider="test-provider", provider_diagram_id=key)
            self.assertEqual(diagram.license_status, Diagram.LicenseStatus.LOCALLY_STORED)
            self.assertIsNotNone(diagram.file_id)
        self.assertFalse(Diagram.objects.filter(provider_diagram_id="FAKE").exists())

    def test_rerun_is_idempotent(self):
        self._run("--license-confirmed")
        output = self._run("--license-confirmed")
        self.assertIn("drawings attached:   0", output)
        self.assertIn("already stored:      2", output)

    def test_an_existing_diagram_keeps_its_parts_and_gains_the_image(self):
        services.import_row(
            services.ImportRow(
                part_number="IMG-00001", description="On an existing figure", manufacturer="Toyota",
                diagram_code="IMG1", provider="test-provider", provider_diagram_id="IMG1", callout="1",
            ),
            services.ImportResult(),
        )
        self._run("--license-confirmed")
        user = User.objects.create_user(email="img-reader@example.com", password="x")
        self.client.force_login(user)
        part = self.client.get(reverse("oem-part-search"), {"q": "IMG-00001"}).data
        diagram = part["diagram_parts"][0]["diagram"]
        self.assertEqual(diagram["license_status"], "LOCALLY_STORED")
        self.assertTrue(diagram["image_url"].endswith("/image/"))
        image = self.client.get(diagram["image_url"])
        self.assertEqual(image.status_code, 200)
        self.assertEqual(b"".join(image.streaming_content), self.PNG)


class FigureOnLocallyStoredDiagramTests(APITestCase):
    def test_figure_import_keeps_a_locally_stored_diagram_and_records_its_source_url(self):
        diagram = Diagram.objects.create(
            provider="test-provider", provider_diagram_id="LOCALFIG", diagram_code="LOCALFIG",
            license_status=Diagram.LicenseStatus.LOCALLY_STORED,
        )
        services.import_figure(
            provider="test-provider", provider_diagram_id="LOCALFIG", diagram_code="LOCALFIG",
            source_image_url="https://example.com/LOCALFIG.png", manufacturer="Toyota",
            figure_data={"groups": [{"callout": "1", "rows": [{"part_number": "LOC-00001"}]}]},
        )
        diagram.refresh_from_db()
        self.assertEqual(diagram.license_status, Diagram.LicenseStatus.LOCALLY_STORED)
        self.assertEqual(diagram.source_image_url, "https://example.com/LOCALFIG.png")
        self.assertTrue(diagram.figure_data)
        self.assertEqual(Diagram.objects.filter(provider="test-provider").count(), 1)
