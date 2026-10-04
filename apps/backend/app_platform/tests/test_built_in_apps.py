"""Built-in application catalog, id stability, status gating and one-click install.

Local Edition §26-27: a shop owner picks an application from a gallery and it is
installed and ready -- no template drafts, no JSON, no API calls -- and only
applications that have actually been qualified are offered to customers.
"""

from unittest.mock import patch

from django.core.management import call_command
from django.db import connections
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import built_in_apps
from app_platform.built_in_apps import CATALOG, BuiltInApp, Status, definition_for, stabilize_ids
from app_platform.models import AppInstance, AppTemplate, QuantityLedgerBinding, RuntimeProvision
from app_platform.reference_templates import REGISTRY
from app_platform.tests.test_foundation import project_for
from organizations.models import Membership
from organizations.services import create_organization
from workspaces.models import Project


class CatalogTests(SimpleTestCase):
    def test_every_reference_template_has_an_honest_catalog_entry(self):
        self.assertEqual(set(CATALOG), set(REGISTRY))
        for app in CATALOG.values():
            self.assertTrue(app.evidence, f"{app.key} must say what its status rests on")

    def test_every_definition_validates_with_all_references_intact(self):
        for key in CATALOG:
            with self.subTest(key=key):
                definition = definition_for(key)  # validate_definition checks every internal reference
                self.assertTrue(definition["models"])

    def test_ids_are_deterministic_across_builds(self):
        for key in CATALOG:
            with self.subTest(key=key):
                self.assertEqual(definition_for(key), definition_for(key))

    def test_the_raw_builders_are_random_which_is_why_ids_are_stabilized(self):
        raw = [REGISTRY["spare_parts"]["builder"]() for _ in range(2)]
        self.assertNotEqual(raw[0]["models"][0]["id"], raw[1]["models"][0]["id"])

    def test_a_newer_release_keeps_the_ids_of_everything_that_already_existed(self):
        builder = REGISTRY["spare_parts"]["builder"]
        v1 = stabilize_ids(builder(), "spare_parts")
        newer = builder()
        next(m for m in newer["models"] if m["key"] == "part")["fields"].append(
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "key": "barcode",
                "label": "Barcode",
                "data_type": "text",
            }
        )
        v2 = stabilize_ids(newer, "spare_parts")
        old_part = next(m for m in v1["models"] if m["key"] == "part")
        new_part = next(m for m in v2["models"] if m["key"] == "part")
        old_ids = {f["key"]: f["id"] for f in old_part["fields"]}
        new_ids = {f["key"]: f["id"] for f in new_part["fields"]}
        self.assertEqual({k: new_ids[k] for k in old_ids}, old_ids)
        self.assertNotIn(new_ids["barcode"], old_ids.values())
        self.assertEqual(v1["relationships"], v2["relationships"])

    def test_the_ledger_declaration_survives_id_stabilization(self):
        ledger = definition_for("spare_parts")["quantity_ledgers"]
        self.assertEqual(len(ledger), 1)  # validate_definition already proved every reference resolves


class GalleryVisibilityTests(SimpleTestCase):
    def test_customers_see_only_qualified_applications_by_default(self):
        with override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=False):
            self.assertTrue(all(a["status"] == "qualified" for a in built_in_apps.listing()))

    def test_the_qualified_flagship_is_the_only_application_customers_are_offered_by_default(self):
        with override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=False):
            shown = {a["key"]: a for a in built_in_apps.listing()}
        self.assertEqual(set(shown), {"spare_parts"})
        self.assertEqual(shown["spare_parts"]["status_label"], "Ready for use")
        self.assertTrue(
            shown["spare_parts"]["evidence"], "a QUALIFIED application must say where its evidence lives"
        )

    def test_every_qualified_application_names_its_evidence(self):
        for app in CATALOG.values():
            if app.status == Status.QUALIFIED:
                self.assertTrue(app.evidence, app.key)
                self.assertTrue(
                    any(line.startswith("docs/") or line.startswith("apps/") for line in app.evidence),
                    app.key,
                )

    def test_a_qualified_application_appears_and_an_unqualified_one_does_not(self):
        promoted = BuiltInApp(
            key="spare_parts",
            label="Spare Parts",
            summary="s",
            highlights=("h",),
            status=Status.QUALIFIED,
            evidence=("proof",),
        )
        with (
            override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=False),
            patch.dict(CATALOG, {"spare_parts": promoted}),
        ):
            self.assertEqual([a["key"] for a in built_in_apps.listing()], ["spare_parts"])

    def test_the_preview_flag_lists_previews_with_their_honest_label_but_never_deferred_apps(self):
        with override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True):
            shown = {a["key"]: a for a in built_in_apps.listing()}
        self.assertEqual(set(shown), {k for k, a in CATALOG.items() if a.status != Status.DEFERRED})
        self.assertEqual(shown["spare_parts"]["status_label"], "Ready for use")
        self.assertEqual(shown["hr"]["status_label"], "Experimental")
        for key in ("crm", "procurement", "assets", "projects", "documents", "warehouses"):
            self.assertEqual(CATALOG[key].status, Status.DEFERRED)
            self.assertNotIn(key, shown)

    def test_visibility_of_every_status_with_and_without_the_preview_flag(self):
        expected = {  # (status, preview flag) -> shown to a customer?
            (Status.QUALIFIED, False): True,
            (Status.QUALIFIED, True): True,
            (Status.PARTIALLY_QUALIFIED, False): False,
            (Status.PARTIALLY_QUALIFIED, True): True,
            (Status.EXPERIMENTAL, False): False,
            (Status.EXPERIMENTAL, True): True,
            (Status.DEFERRED, False): False,
            (Status.DEFERRED, True): False,
        }
        for (status, flag), shown in expected.items():
            app = BuiltInApp(
                key="spare_parts", label="x", summary="s", highlights=("h",), status=status, evidence=("e",)
            )
            with self.subTest(status=status.value, preview=flag):
                with (
                    override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=flag),
                    patch.dict(CATALOG, {"spare_parts": app}),
                ):
                    self.assertEqual("spare_parts" in {a["key"] for a in built_in_apps.listing()}, shown)

    def test_hr_does_not_advertise_payroll(self):
        hr = CATALOG["hr"]
        self.assertNotIn("payroll", (hr.summary + " ".join(hr.highlights)).lower())
        self.assertIn("not a payroll feature", " ".join(hr.evidence))


class InstallTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="builtin-owner@example.com")
        self.org = create_organization(name="Builtin Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.url = f"/api/v1/projects/{self.project.id}/built-in-apps/spare_parts/install/"

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            for receipt in RuntimeProvision.objects.all():
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(receipt.plan["schema_name"])
                    )
                )
        super().tearDown()

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_one_call_installs_and_provisions_a_working_application_with_its_ledger(self):
        response = self.client.post(self.url, {"label": "My Parts Shop"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        instance = AppInstance.objects.get(pk=response.data["id"])
        self.assertEqual(instance.label, "My Parts Shop")
        self.assertTrue(RuntimeProvision.objects.get(instance=instance).completed_at)
        self.assertEqual(QuantityLedgerBinding.objects.filter(instance=instance).count(), 1)
        part = instance.models.get(key="part")
        created = self.client.post(
            f"/api/v1/app-models/{part.id}/records/",
            {str(part.fields.get(key="name").id): "Oil Filter"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_installing_twice_reuses_one_template_and_one_version(self):
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 201)
        self.assertEqual(self.client.post(self.url, {"label": "Second Shop"}, format="json").status_code, 201)
        templates = AppTemplate.objects.filter(organization=self.org)
        self.assertEqual(templates.count(), 1)
        self.assertEqual(templates.get().versions.count(), 1)
        self.assertEqual(AppInstance.objects.filter(organization=self.org).count(), 2)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_a_changed_release_publishes_exactly_one_new_version_keeping_lineage(self):
        self.client.post(self.url, {}, format="json")
        changed = definition_for("spare_parts")
        next(m for m in changed["models"] if m["key"] == "part")["fields"].append(
            {
                "id": "00000000-0000-4000-8000-000000000002",
                "key": "barcode",
                "label": "Barcode",
                "data_type": "text",
                "required": False,
                "default_value": None,
                "unique": False,
                "indexed": False,
            }
        )
        with patch.object(built_in_apps, "definition_for", return_value=changed):
            self.assertEqual(
                self.client.post(self.url, {"label": "After Release"}, format="json").status_code, 201
            )
        template = AppTemplate.objects.get(organization=self.org)
        self.assertEqual([v.number for v in template.versions.all()], [1, 2])

    def test_an_application_that_is_not_shown_to_customers_cannot_be_installed(self):
        # HR is EXPERIMENTAL, not QUALIFIED, so it is not offered by default.
        hr_url = f"/api/v1/projects/{self.project.id}/built-in-apps/hr/install/"
        with override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=False):
            response = self.client.post(hr_url, {}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(AppInstance.objects.filter(organization=self.org).exists())

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_a_deferred_application_cannot_be_installed_even_in_preview_mode(self):
        url = f"/api/v1/projects/{self.project.id}/built-in-apps/crm/install/"
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 404)
        self.assertFalse(AppInstance.objects.filter(organization=self.org).exists())

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=False)
    def test_a_qualified_application_installs_with_no_preview_flag(self):
        promoted = BuiltInApp(
            key="spare_parts",
            label="Spare Parts",
            summary="s",
            highlights=("h",),
            status=Status.QUALIFIED,
            evidence=("proof",),
        )
        with patch.dict(CATALOG, {"spare_parts": promoted}):
            self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 201)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_an_unknown_application_is_not_found(self):
        url = f"/api/v1/projects/{self.project.id}/built-in-apps/nope/install/"
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 404)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_a_member_without_the_capabilities_is_denied_and_nothing_is_created(self):
        member = User.objects.create_user(email="builtin-member@example.com")
        Membership.objects.create(user=member, organization=self.org, status=Membership.Status.ACTIVE)
        client = APIClient()
        client.force_authenticate(member)
        response = client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(AppTemplate.objects.filter(organization=self.org).exists())
        self.assertFalse(AppInstance.objects.filter(organization=self.org).exists())

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_another_organizations_project_is_not_reachable(self):
        outsider = User.objects.create_user(email="builtin-outsider@example.com")
        create_organization(name="Other Org", created_by=outsider)
        client = APIClient()
        client.force_authenticate(outsider)
        self.assertEqual(client.post(self.url, {}, format="json").status_code, 404)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_a_provisioning_failure_is_reported_plainly_without_a_traceback(self):
        with patch(
            "app_platform.built_in_apps.provisioning.execute", side_effect=RuntimeError("secret internals")
        ):
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("secret internals", str(response.data))
        self.assertIn("could not be prepared", str(response.data))

    def test_the_gallery_requires_a_login(self):
        self.assertIn(APIClient().get("/api/v1/built-in-apps/").status_code, (401, 403))

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_the_gallery_endpoint_lists_the_non_deferred_catalog_for_a_signed_in_user(self):
        response = self.client.get("/api/v1/built-in-apps/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {a["key"] for a in response.data["results"]},
            {k for k, a in CATALOG.items() if a.status != Status.DEFERRED},
        )


class InstalledStateTests(TransactionTestCase):
    """The gallery must know, per project: is it installed, which instance, and is its
    runtime ready, pending or failed -- and a failed setup must be safely retryable."""

    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="state-owner@example.com")
        self.org = create_organization(name="State Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)
        self.other_project = Project.objects.create(
            workspace=self.project.workspace, name="Second Project", created_by=self.owner
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.install_url = f"/api/v1/projects/{self.project.id}/built-in-apps/spare_parts/install/"

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            for receipt in RuntimeProvision.objects.all():
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(receipt.plan["schema_name"])
                    )
                )
        super().tearDown()

    def _entry(self, project=None):
        response = self.client.get("/api/v1/built-in-apps/", {"project": str((project or self.project).id)})
        self.assertEqual(response.status_code, 200, response.data)
        return next(a for a in response.data["results"] if a["key"] == "spare_parts")

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_the_listing_reports_not_installed_then_installed_and_ready(self):
        self.assertEqual(self._entry()["installed"], [])
        created = self.client.post(self.install_url, {"label": "Main Shop"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        installed = self._entry()["installed"]
        self.assertEqual(
            installed, [{"id": str(created.data["id"]), "label": "Main Shop", "runtime": "ready"}]
        )

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_installed_is_per_project(self):
        self.client.post(self.install_url, {}, format="json")
        self.assertEqual(len(self._entry()["installed"]), 1)
        self.assertEqual(self._entry(self.other_project)["installed"], [])

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_the_listing_without_a_project_carries_no_installed_state(self):
        response = self.client.get("/api/v1/built-in-apps/")
        self.assertTrue(all(a["installed"] == [] for a in response.data["results"]))

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_a_project_the_caller_is_not_a_member_of_is_not_found(self):
        outsider = User.objects.create_user(email="state-outsider@example.com")
        create_organization(name="Elsewhere", created_by=outsider)
        client = APIClient()
        client.force_authenticate(outsider)
        response = client.get("/api/v1/built-in-apps/", {"project": str(self.project.id)})
        self.assertEqual(response.status_code, 404)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_a_malformed_project_id_is_a_clean_400(self):
        self.assertEqual(self.client.get("/api/v1/built-in-apps/", {"project": "nope"}).status_code, 400)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_a_member_who_cannot_read_instances_sees_none_listed(self):
        self.client.post(self.install_url, {}, format="json")
        member = User.objects.create_user(email="state-member@example.com")
        Membership.objects.create(user=member, organization=self.org, status=Membership.Status.ACTIVE)
        client = APIClient()
        client.force_authenticate(member)
        response = client.get("/api/v1/built-in-apps/", {"project": str(self.project.id)})
        entry = next(a for a in response.data["results"] if a["key"] == "spare_parts")
        self.assertEqual(entry["installed"], [])

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_a_failed_setup_is_reported_and_can_be_retried_to_ready(self):
        with patch("app_platform.built_in_apps.provisioning.execute", side_effect=RuntimeError("boom")):
            failed = self.client.post(self.install_url, {"label": "Half Shop"}, format="json")
        self.assertEqual(failed.status_code, 500)
        [entry] = self._entry()["installed"]
        self.assertEqual(entry["label"], "Half Shop")
        self.assertNotEqual(entry["runtime"], "ready")

        retry = self.client.post(f"/api/v1/app-instances/{entry['id']}/built-in/retry/", {}, format="json")
        self.assertEqual(retry.status_code, 200, retry.data)
        self.assertEqual(
            self._entry()["installed"], [{"id": entry["id"], "label": "Half Shop", "runtime": "ready"}]
        )
        self.assertEqual(AppInstance.objects.filter(organization=self.org).count(), 1)  # no second instance

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_retrying_an_already_ready_application_is_a_harmless_no_op(self):
        created = self.client.post(self.install_url, {}, format="json")
        again = self.client.post(
            f"/api/v1/app-instances/{created.data['id']}/built-in/retry/", {}, format="json"
        )
        self.assertEqual(again.status_code, 200, again.data)
        self.assertEqual(QuantityLedgerBinding.objects.filter(instance_id=created.data["id"]).count(), 1)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_retry_is_refused_for_an_instance_that_is_not_a_built_in_application(self):
        from app_platform import instances, templates
        from app_platform.tests.test_foundation import sample

        template = templates.create_template(self.owner, self.org, {"label": "Hand made", "draft": sample()})
        version = templates.publish_template(self.owner, template)
        manual = instances.install(
            self.owner, self.project, {"label": "Manual", "template_version": str(version.id)}
        )
        response = self.client.post(f"/api/v1/app-instances/{manual.id}/built-in/retry/", {}, format="json")
        self.assertEqual(response.status_code, 404)

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=True)
    def test_retry_by_another_organizations_user_is_not_found(self):
        created = self.client.post(self.install_url, {}, format="json")
        outsider = User.objects.create_user(email="retry-outsider@example.com")
        create_organization(name="Retry Elsewhere", created_by=outsider)
        client = APIClient()
        client.force_authenticate(outsider)
        response = client.post(
            f"/api/v1/app-instances/{created.data['id']}/built-in/retry/", {}, format="json"
        )
        self.assertEqual(response.status_code, 404)
