"""Movie Shop additions: music and albums, the owner's own poster (kept through re-scans), renaming, editing a
customer, and password recovery that only the owner can allow (the portal password and the IF Pay wallet)."""

from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from app_platform.tests.test_foundation import project_for
from movie_shop.models import MovieShop, PasswordResetCode, PortalCustomer, Title
from movie_shop.tests.test_ads import png
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission

HEADER = {"HTTP_X_PORTAL_REQUEST": "1"}
PASSWORD = "Portal-pass-2026"
PAY = "movie_shop.portal.pay_bridge"


class MoreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="more-owner@example.com")
        cls.org = create_organization(name="More Movies", created_by=cls.owner)
        cls.project = project_for(cls.owner, cls.org)
        cls.clerk = User.objects.create_user(email="more-clerk@example.com")
        Membership.objects.create(user=cls.clerk, organization=cls.org, status=Membership.Status.ACTIVE)
        cls.outsider = User.objects.create_user(email="more-outsider@example.com")
        create_organization(name="Somewhere else", created_by=cls.outsider)

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_login(self.owner)
        data = self.client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Music and Movies", "project": str(self.project.id)},
            format="json",
        ).data
        self.shop = MovieShop.objects.get(pk=data["id"])
        token = self.client.post(f"/api/v1/movie-shops/{self.shop.id}/agent-credential/").data["token"]
        self.agent = APIClient()
        self.agent.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.lib = self.client.post(
            f"/api/v1/movie-shops/{self.shop.id}/libraries/", {"path": "D:\\Media"}, format="json"
        ).data

    def scan(self, titles):
        gen = self.agent.post(
            f"/api/v1/movie-agent/libraries/{self.lib['id']}/scan/start/", {}, format="json"
        ).data["generation"]
        r = self.agent.post(
            f"/api/v1/movie-agent/libraries/{self.lib['id']}/scan/titles/",
            {"generation": gen, "titles": titles},
            format="json",
        )
        self.agent.post(
            f"/api/v1/movie-agent/libraries/{self.lib['id']}/scan/finish/", {"generation": gen}, format="json"
        )
        return r

    def manager(self):
        clerk = APIClient()
        clerk.force_login(self.clerk)
        grant_resource_permission(
            user=self.clerk,
            organization_id=self.org.id,
            permission_code="movies.sell",
            resource_type="movie_shop",
            resource_id=str(self.shop.id),
            granted_by=self.owner,
        )
        return clerk

    # ---- music ---------------------------------------------------------------------------------------------
    def test_songs_and_albums_are_titles_like_films(self):
        r = self.scan(
            [
                {
                    "relative_path": "Music\\Tizita.mp3",
                    "category": "Music",
                    "title": "Tizita",
                    "kind": "music",
                },
                {
                    "relative_path": "Music\\Ethiopia (2017)",
                    "category": "Music",
                    "title": "Ethiopia",
                    "kind": "album",
                    "episodes": 14,
                },
            ]
        )
        self.assertEqual(r.status_code, 200, r.data)
        kinds = dict(Title.objects.values_list("title", "kind"))
        self.assertEqual(kinds, {"Tizita": "music", "Ethiopia": "album"})
        bad = self.scan([{"relative_path": "x.mp3", "category": "M", "title": "X", "kind": "podcast"}])
        self.assertEqual(bad.status_code, 400)

    # ---- the owner's poster --------------------------------------------------------------------------------
    def test_the_owners_poster_stays_through_rescans_until_cleared(self):
        self.scan(
            [
                {
                    "relative_path": "Action\\Desert Wind.mp4",
                    "category": "Action",
                    "title": "Desert Wind",
                    "cover_fingerprint": "1-1",
                }
            ]
        )
        title = Title.objects.get()
        url = f"/api/v1/movie-titles/{title.id}/cover/"
        self.assertEqual(
            self.manager()
            .post(url, {"file": SimpleUploadedFile("p.png", png())}, format="multipart")
            .status_code,
            403,
        )
        fake = SimpleUploadedFile("p.png", b"not a picture", content_type="image/png")
        self.assertEqual(self.client.post(url, {"file": fake}, format="multipart").status_code, 400)
        r = self.client.post(
            url, {"file": SimpleUploadedFile("p.png", png(), content_type="image/png")}, format="multipart"
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data["cover_locked"] and r.data["has_cover"])
        # The folder's picture changed: the agent is not asked for it, and an upload would not replace it.
        again = self.scan(
            [
                {
                    "relative_path": "Action\\Desert Wind.mp4",
                    "category": "Action",
                    "title": "Desert Wind",
                    "cover_fingerprint": "2-2",
                }
            ]
        )
        self.assertEqual(again.data["covers_wanted"], [])
        self.assertEqual(self.client.get(url).content, png())
        cleared = self.client.delete(url).data
        self.assertEqual((cleared["cover_locked"], cleared["has_cover"]), (False, False))
        third = self.scan(
            [
                {
                    "relative_path": "Action\\Desert Wind.mp4",
                    "category": "Action",
                    "title": "Desert Wind",
                    "cover_fingerprint": "2-2",
                }
            ]
        )
        self.assertEqual(third.data["covers_wanted"], ["Action\\Desert Wind.mp4"])

    # ---- renaming ------------------------------------------------------------------------------------------
    def test_renaming_the_shop_and_a_library(self):
        self.client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Taken", "project": str(self.project.id)},
            format="json",
        )
        url = f"/api/v1/movie-shops/{self.shop.id}/"
        self.assertEqual(self.client.patch(url, {"name": "Taken"}, format="json").status_code, 400)
        self.assertEqual(
            self.client.patch(url, {"name": "Lamek Media"}, format="json").data["name"], "Lamek Media"
        )
        self.assertEqual(self.manager().patch(url, {"name": "X"}, format="json").status_code, 403)
        outsider = APIClient()
        outsider.force_login(self.outsider)
        self.assertEqual(outsider.patch(url, {"name": "X"}, format="json").status_code, 404)
        lib = self.client.patch(
            f"/api/v1/movie-libraries/{self.lib['id']}/", {"name": "Big disk"}, format="json"
        )
        self.assertEqual(lib.data["name"], "Big disk")

    # ---- customers -----------------------------------------------------------------------------------------
    def customer(self, phone="0911223344"):
        self.client.put(f"/api/v1/movie-shops/{self.shop.id}/portal/", {"portal_open": True}, format="json")
        portal = APIClient()
        r = portal.post(
            f"/api/v1/portal/{self.shop.id}/signup/",
            {"name": "Selam", "phone": phone, "password": PASSWORD},
            format="json",
            **HEADER,
        )
        self.assertEqual(r.status_code, 201, r.data)
        return portal, PortalCustomer.objects.get(id=r.data["id"])

    def test_the_owner_corrects_a_customer(self):
        _, c = self.customer()
        self.customer(phone="0922000000")
        url = f"/api/v1/movie-customers/{c.id}/"
        self.assertEqual(self.client.patch(url, {"phone": "0922000000"}, format="json").status_code, 400)
        r = self.client.patch(url, {"name": "Selam T.", "birthday": "1995-04-21"}, format="json")
        self.assertEqual(
            (r.data["customer"]["name"], r.data["customer"]["birthday"]), ("Selam T.", "1995-04-21")
        )
        self.assertEqual(self.client.patch(url, {"status": "approved"}, format="json").status_code, 400)

    def test_password_recovery_needs_the_owners_one_time_code(self):
        portal, c = self.customer()
        base = f"/api/v1/portal/{self.shop.id}"
        # Asking says the same for a phone with or without an account.
        self.assertEqual(
            APIClient().post(f"{base}/forgot/", {"phone": "0999999999"}, format="json", **HEADER).data,
            {"ok": True},
        )
        self.assertEqual(
            APIClient().post(f"{base}/forgot/", {"phone": c.phone}, format="json", **HEADER).data,
            {"ok": True},
        )
        c.refresh_from_db()
        self.assertIsNotNone(c.reset_requested_at)
        listed = self.client.get(f"/api/v1/movie-shops/{self.shop.id}/customers/").data["results"][0]
        self.assertIsNotNone(listed["reset_requested_at"])
        # No code yet: nothing works.
        guess = APIClient().post(
            f"{base}/reset/",
            {"phone": c.phone, "code": "AAAA-BBBB", "password": "New-pass-2026"},
            format="json",
            **HEADER,
        )
        self.assertEqual(guess.status_code, 401)
        self.assertEqual(self.manager().post(f"/api/v1/movie-customers/{c.id}/reset-code/").status_code, 403)
        code = self.client.post(f"/api/v1/movie-customers/{c.id}/reset-code/").data["code"]
        self.assertNotIn(
            code.replace("-", ""), str(PasswordResetCode.objects.values_list("code_hash", flat=True)[0])
        )
        ok = APIClient().post(
            f"{base}/reset/",
            {"phone": c.phone, "code": code.lower(), "password": "New-pass-2026"},
            format="json",
            **HEADER,
        )
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(portal.get(f"{base}/me/").status_code, 401)  # the old sign-in ended
        old = APIClient().post(
            f"{base}/login/", {"phone": c.phone, "password": PASSWORD}, format="json", **HEADER
        )
        self.assertEqual(old.status_code, 401)
        new = APIClient().post(
            f"{base}/login/", {"phone": c.phone, "password": "New-pass-2026"}, format="json", **HEADER
        )
        self.assertEqual(new.status_code, 200)
        again = APIClient().post(
            f"{base}/reset/",
            {"phone": c.phone, "code": code, "password": "Other-pass-2026"},
            format="json",
            **HEADER,
        )
        self.assertEqual(again.status_code, 401)  # a code works once
        c.refresh_from_db()
        self.assertIsNone(c.reset_requested_at)

    def test_a_reset_code_stops_after_five_wrong_tries(self):
        _, c = self.customer()
        base = f"/api/v1/portal/{self.shop.id}"
        code = self.client.post(f"/api/v1/movie-customers/{c.id}/reset-code/").data["code"]
        for _ in range(5):
            APIClient().post(
                f"{base}/reset/",
                {"phone": c.phone, "code": "WRONG123", "password": "New-pass-2026"},
                format="json",
                **HEADER,
            )
            cache.clear()  # the auth throttle is not what this test is about
        right = APIClient().post(
            f"{base}/reset/",
            {"phone": c.phone, "code": code, "password": "New-pass-2026"},
            format="json",
            **HEADER,
        )
        self.assertEqual(right.status_code, 401)

    def test_the_owner_can_give_a_wallet_a_new_one_time_password(self):
        _, c = self.customer()
        url = f"/api/v1/movie-customers/{c.id}/wallet-password/"
        self.assertEqual(self.client.post(url).status_code, 400)  # no wallet yet
        c.pay_wallet_id = "6f1c1c4e-2b3a-4c1d-9e2f-0123456789ab"
        c.status = PortalCustomer.Status.APPROVED
        c.save()
        with mock.patch(PAY) as pay:
            pay.reset_customer_wallet_password.return_value = {
                "username": "selam",
                "first_password": "k7mq-x2vd-9tna",
            }
            r = self.client.post(url)
        self.assertEqual(r.data["wallet"], {"username": "selam", "first_password": "k7mq-x2vd-9tna"})
        self.assertEqual(pay.reset_customer_wallet_password.call_args.kwargs["actor_id"], self.owner.pk)
        self.assertEqual(self.manager().post(url).status_code, 403)
