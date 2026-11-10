"""Movie Shop phase 1 (ADR-0022): who may do what, organization isolation, the media agent's credential,
scanning and covers -- against the real database and object storage."""

import struct
import zlib

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from app_platform.tests.test_foundation import project_for
from applications import services as applications
from movie_shop.models import Library, MovieShop, Title
from organizations.models import Membership
from organizations.services import create_organization


def png_bytes() -> bytes:
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = b"\x00\xff\x80\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class MovieShopTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="movie-owner@example.com")
        cls.org = create_organization(name="Lamek Movies", created_by=cls.owner)
        cls.project = project_for(cls.owner, cls.org)
        cls.clerk = User.objects.create_user(email="movie-clerk@example.com")
        Membership.objects.create(user=cls.clerk, organization=cls.org, status=Membership.Status.ACTIVE)
        cls.outsider = User.objects.create_user(email="movie-outsider@example.com")
        cls.other_org = create_organization(name="Other Movies", created_by=cls.outsider)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.owner)
        created = self.client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Lamek Movie Shop", "project": str(self.project.id)},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.shop = MovieShop.objects.get(pk=created.data["id"])
        token = self.client.post(f"/api/v1/movie-shops/{self.shop.id}/agent-credential/").data["token"]
        self.agent = APIClient()
        self.agent.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def report(self, client=None):
        return (client or self.agent).post(
            "/api/v1/movie-agent/report/",
            {
                "computer": "SHOP-PC",
                "agent_version": "1.0",
                "drives": [
                    {
                        "root": "D:\\",
                        "label": "Movies",
                        "kind": "fixed",
                        "total_bytes": 4 * 10**12,
                        "free_bytes": 2 * 10**12,
                        "folders": ["D:\\Movies", "D:\\Series"],
                    }
                ],
            },
            format="json",
        )

    def library(self) -> Library:
        return Library.objects.get(
            pk=self.client.post(
                f"/api/v1/movie-shops/{self.shop.id}/libraries/",
                {"path": "D:\\Movies", "name": "Movies drive (D:)"},
                format="json",
            ).data["id"]
        )

    def scan(self, library, titles):
        generation = self.agent.post(
            f"/api/v1/movie-agent/libraries/{library.id}/scan/start/", {}, format="json"
        ).data["generation"]
        batch = self.agent.post(
            f"/api/v1/movie-agent/libraries/{library.id}/scan/titles/",
            {"generation": generation, "titles": titles},
            format="json",
        )
        self.assertEqual(batch.status_code, 200, batch.data)
        done = self.agent.post(
            f"/api/v1/movie-agent/libraries/{library.id}/scan/finish/",
            {"generation": generation},
            format="json",
        )
        self.assertEqual(done.status_code, 200, done.data)
        return batch.data

    # ---- who may do what -----------------------------------------------------------------------------------
    def test_creating_a_shop_registers_its_agent_application_and_covers_bucket(self):
        self.assertIsNotNone(self.shop.agent_application)
        self.assertIsNotNone(self.shop.covers_bucket)
        self.assertEqual(self.shop.covers_bucket.project_id, self.project.id)

    def test_a_member_without_the_capability_cannot_see_or_manage_a_shop(self):
        clerk = APIClient()
        clerk.force_login(self.clerk)
        self.assertEqual(clerk.get(f"/api/v1/movie-shops/{self.shop.id}/").status_code, 403)
        self.assertEqual(clerk.get(f"/api/v1/organizations/{self.org.id}/movie-shops/").data, [])
        self.assertEqual(
            clerk.post(
                f"/api/v1/organizations/{self.org.id}/movie-shops/",
                {"name": "X", "project": str(self.project.id)},
                format="json",
            ).status_code,
            403,
        )

    def test_another_organization_cannot_reach_the_shop_or_its_titles(self):
        library = self.library()
        self.scan(
            library,
            [
                {
                    "relative_path": "Action\\Desert Wind (2025).mp4",
                    "category": "Action",
                    "title": "Desert Wind",
                    "year": 2025,
                }
            ],
        )
        title = Title.objects.get()
        outsider = APIClient()
        outsider.force_login(self.outsider)
        for url in (
            f"/api/v1/movie-shops/{self.shop.id}/",
            f"/api/v1/movie-shops/{self.shop.id}/titles/",
            f"/api/v1/movie-titles/{title.id}/cover/",
            f"/api/v1/movie-libraries/{library.id}/scan/",
        ):
            response = outsider.get(url) if "scan" not in url else outsider.post(url)
            self.assertEqual(response.status_code, 404, url)
        self.assertEqual(
            outsider.patch(f"/api/v1/movie-titles/{title.id}/", {"price": 1}, format="json").status_code, 404
        )

    # ---- the media agent's credential ----------------------------------------------------------------------
    def test_the_agent_reports_drives_and_gets_its_work(self):
        self.library()
        response = self.report()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["libraries"][0]["path"], "D:\\Movies")
        self.assertTrue(response.data["libraries"][0]["scan"])
        drives = self.client.get(f"/api/v1/movie-shops/{self.shop.id}/drives/").data
        self.assertEqual(drives["drives"][0]["folders"], ["D:\\Movies", "D:\\Series"])

    def test_a_new_credential_cuts_the_old_one_off(self):
        self.client.post(f"/api/v1/movie-shops/{self.shop.id}/agent-credential/")
        self.assertIn(self.report().status_code, (401, 403))

    def test_another_applications_credential_and_a_browser_session_are_refused_at_agent_endpoints(self):
        other_app = applications.register_application(
            organization=self.org, name="Other app", description="", owner=self.owner
        )
        _, token = applications.issue_credential(service_account=other_app.service_account, actor=self.owner)
        stranger = APIClient()
        stranger.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.report(stranger).status_code, 404)
        self.assertIn(self.report(self.client).status_code, (401, 403))

    def test_the_agent_credential_cannot_use_owner_endpoints(self):
        self.assertIn(self.agent.get(f"/api/v1/movie-shops/{self.shop.id}/").status_code, (401, 403))
        self.assertIn(
            self.agent.post(f"/api/v1/movie-shops/{self.shop.id}/agent-credential/").status_code, (401, 403)
        )

    def test_another_shops_agent_cannot_touch_this_shops_library(self):
        other = self.client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Second shop", "project": str(self.project.id)},
            format="json",
        ).data
        token = self.client.post(f"/api/v1/movie-shops/{other['id']}/agent-credential/").data["token"]
        agent2 = APIClient()
        agent2.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        library = self.library()
        self.assertEqual(
            agent2.post(
                f"/api/v1/movie-agent/libraries/{library.id}/scan/start/", {}, format="json"
            ).status_code,
            404,
        )

    # ---- scanning ------------------------------------------------------------------------------------------
    def test_a_rescan_keeps_the_owners_price_hidden_flag_and_edits_and_drops_titles_that_are_gone(self):
        library = self.library()
        self.scan(
            library,
            [
                {
                    "relative_path": "Action\\Desert Wind (2025).mp4",
                    "category": "Action",
                    "title": "Desert Wind",
                    "year": 2025,
                    "size_bytes": 2_100_000_000,
                },
                {
                    "relative_path": "Action\\Red Mountain (2024).mkv",
                    "category": "Action",
                    "title": "Red Mountain",
                    "year": 2024,
                },
                {
                    "relative_path": "Series\\The Coffee House",
                    "category": "Series",
                    "title": "The Coffee House",
                    "kind": "series",
                    "episodes": 30,
                },
            ],
        )
        desert = Title.objects.get(title="Desert Wind")
        self.client.patch(
            f"/api/v1/movie-titles/{desert.id}/",
            {"price": 75, "title": "Desert Wind (Director's cut)"},
            format="json",
        )
        coffee = Title.objects.get(title="The Coffee House")
        self.client.patch(f"/api/v1/movie-titles/{coffee.id}/", {"hidden": True}, format="json")
        self.scan(
            library,
            [
                {
                    "relative_path": "Action\\Desert Wind (2025).mp4",
                    "category": "Action",
                    "title": "Desert Wind",
                    "year": 2025,
                },
                {
                    "relative_path": "Series\\The Coffee House",
                    "category": "Series",
                    "title": "The Coffee House",
                    "kind": "series",
                    "episodes": 40,
                },
            ],
        )
        desert.refresh_from_db()
        coffee.refresh_from_db()
        self.assertEqual((desert.price, desert.title), (75, "Desert Wind (Director's cut)"))
        self.assertTrue(coffee.hidden)
        self.assertEqual(coffee.episodes, 40)
        self.assertFalse(Title.objects.filter(title="Red Mountain").exists())
        library.refresh_from_db()
        self.assertIsNone(library.scan_requested_at)

    def test_prices_come_from_the_title_then_its_category_then_the_shop(self):
        library = self.library()
        self.scan(
            library,
            [
                {"relative_path": "Kids\\Little Camel.mp4", "category": "Kids", "title": "Little Camel"},
                {"relative_path": "Action\\Zero Hour.mp4", "category": "Action", "title": "Zero Hour"},
            ],
        )
        self.client.put(
            f"/api/v1/movie-shops/{self.shop.id}/prices/",
            {"default_price": 40, "categories": {"Kids": 30}},
            format="json",
        )
        titles = {
            t["title"]: t["price"]
            for t in self.client.get(f"/api/v1/movie-shops/{self.shop.id}/titles/").data["results"]
        }
        self.assertEqual(titles, {"Little Camel": 30, "Zero Hour": 40})
        cats = self.client.get(f"/api/v1/movie-shops/{self.shop.id}/categories/").data
        self.assertEqual({c["name"]: c["count"] for c in cats}, {"Action": 1, "Kids": 1})

    def test_paths_outside_a_library_and_device_paths_are_refused(self):
        for path in (
            "..\\Windows",
            "C:Movies",
            "\\\\?\\C:\\Movies",
            "D:\\Movies\\..\\Windows",
            "relative\\folder",
        ):
            response = self.client.post(
                f"/api/v1/movie-shops/{self.shop.id}/libraries/", {"path": path}, format="json"
            )
            self.assertEqual(response.status_code, 400, path)
        library = self.library()
        generation = self.agent.post(
            f"/api/v1/movie-agent/libraries/{library.id}/scan/start/", {}, format="json"
        ).data["generation"]
        for rel in ("..\\secret.mp4", "C:\\Windows\\a.mp4", "\\root.mp4"):
            response = self.agent.post(
                f"/api/v1/movie-agent/libraries/{library.id}/scan/titles/",
                {"generation": generation, "titles": [{"relative_path": rel, "category": "X", "title": "X"}]},
                format="json",
            )
            self.assertEqual(response.status_code, 400, rel)

    def test_an_old_scan_cannot_overwrite_a_newer_one(self):
        library = self.library()
        first = self.agent.post(
            f"/api/v1/movie-agent/libraries/{library.id}/scan/start/", {}, format="json"
        ).data["generation"]
        self.agent.post(f"/api/v1/movie-agent/libraries/{library.id}/scan/start/", {}, format="json")
        stale = self.agent.post(
            f"/api/v1/movie-agent/libraries/{library.id}/scan/finish/", {"generation": first}, format="json"
        )
        self.assertEqual(stale.status_code, 400)

    # ---- covers --------------------------------------------------------------------------------------------
    def test_a_cover_is_stored_as_a_file_and_served_to_the_owner_only(self):
        library = self.library()
        wanted = self.scan(
            library,
            [
                {
                    "relative_path": "Action\\Desert Wind (2025).mp4",
                    "category": "Action",
                    "title": "Desert Wind",
                    "cover_fingerprint": "123-456",
                }
            ],
        )
        self.assertEqual(wanted["covers_wanted"], ["Action\\Desert Wind (2025).mp4"])
        upload = self.agent.post(
            f"/api/v1/movie-agent/libraries/{library.id}/covers/",
            {
                "relative_path": "Action\\Desert Wind (2025).mp4",
                "fingerprint": "123-456",
                "file": SimpleUploadedFile("c.png", png_bytes(), content_type="image/png"),
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201, upload.data)
        title = Title.objects.get()
        self.assertEqual(title.cover.bucket_id, self.shop.covers_bucket_id)
        cover = self.client.get(f"/api/v1/movie-titles/{title.id}/cover/")
        self.assertEqual(cover.status_code, 200)
        self.assertEqual(cover["Content-Type"], "image/png")
        self.assertTrue(b"".join(cover).startswith(b"\x89PNG"))
        # The same picture again is not asked for.
        again = self.scan(
            library,
            [
                {
                    "relative_path": "Action\\Desert Wind (2025).mp4",
                    "category": "Action",
                    "title": "Desert Wind",
                    "cover_fingerprint": "123-456",
                }
            ],
        )
        self.assertEqual(again["covers_wanted"], [])

    def test_a_cover_must_be_a_picture(self):
        library = self.library()
        self.scan(library, [{"relative_path": "a.mp4", "category": "Other", "title": "A"}])
        response = self.agent.post(
            f"/api/v1/movie-agent/libraries/{library.id}/covers/",
            {
                "relative_path": "a.mp4",
                "file": SimpleUploadedFile("c.png", b"<script>alert(1)</script>", content_type="image/png"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(Title.objects.get().cover)
