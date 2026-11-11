"""Movie Shop phase 4 (ADR-0022 decision 8): ads on the shop's own portal -- managed with movies.manage, shown
only while switched on and within their dates, safe links only, real pictures only, views and taps counted."""

import datetime
import io
import struct
import zlib

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from app_platform.tests.test_foundation import project_for
from movie_shop.models import Ad, MovieShop, Title
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission

HEADER = {"HTTP_X_PORTAL_REQUEST": "1"}


def png() -> bytes:
    """A real 1x1 PNG."""

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = b"\x00\xff\x99\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class AdTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="ads-owner@example.com")
        cls.org = create_organization(name="Ads Movies", created_by=cls.owner)
        cls.project = project_for(cls.owner, cls.org)
        cls.clerk = User.objects.create_user(email="ads-clerk@example.com")
        Membership.objects.create(user=cls.clerk, organization=cls.org, status=Membership.Status.ACTIVE)
        cls.outsider = User.objects.create_user(email="ads-outsider@example.com")
        create_organization(name="Elsewhere", created_by=cls.outsider)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.owner)
        data = self.client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Ad Shop", "project": str(self.project.id)},
            format="json",
        ).data
        self.shop = MovieShop.objects.get(pk=data["id"])
        self.client.post(f"/api/v1/movie-shops/{self.shop.id}/agent-credential/")
        self.client.put(f"/api/v1/movie-shops/{self.shop.id}/portal/", {"portal_open": True}, format="json")
        lib = self.shop.libraries.create(name="Movies", path="D:\\Movies")
        self.film = Title.objects.create(
            shop=self.shop,
            library=lib,
            relative_path="Action\\Desert Wind.mp4",
            category="Action",
            title="Desert Wind",
        )

    def create(self, **data):
        return self.client.post(
            f"/api/v1/movie-shops/{self.shop.id}/ads/", {"title": "Big sale", **data}, format="json"
        )

    def portal_ads(self):
        return APIClient().get(f"/api/v1/portal/{self.shop.id}/ads/").data

    def test_only_movies_manage_manages_ads_and_other_organizations_see_nothing(self):
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
        self.assertEqual(
            clerk.post(f"/api/v1/movie-shops/{self.shop.id}/ads/", {"title": "x"}, format="json").status_code,
            403,
        )
        ad = self.create().data
        self.assertEqual(
            clerk.patch(f"/api/v1/movie-ads/{ad['id']}/", {"title": "y"}, format="json").status_code, 403
        )
        outsider = APIClient()
        outsider.force_login(self.outsider)
        self.assertEqual(outsider.get(f"/api/v1/movie-shops/{self.shop.id}/ads/").status_code, 404)
        self.assertEqual(outsider.delete(f"/api/v1/movie-ads/{ad['id']}/").status_code, 404)

    def test_links_must_be_web_addresses_and_films_must_be_the_shops_own(self):
        for bad in (
            "javascript:alert(1)",
            "data:text/html,x",
            "ftp://x.org",
            "https://",
            'https://x.org/"onload=1',
        ):
            self.assertEqual(self.create(link=bad).status_code, 400, bad)
        self.assertEqual(self.create(link="https://phones.example/offer?id=1").status_code, 201)
        other_org = create_organization(name="Third", created_by=self.outsider)
        other = MovieShop.objects.create(
            organization=other_org,
            project=project_for(self.outsider, other_org),
            name="Other",
            created_by=self.outsider,
        )
        foreign = Title.objects.create(
            shop=other,
            library=other.libraries.create(name="M", path="E:\\M"),
            relative_path="x.mp4",
            category="A",
            title="X",
        )
        self.assertEqual(self.create(film=str(foreign.id)).status_code, 400)
        self.assertEqual(self.create(film=str(self.film.id), link="https://x.org").status_code, 400)
        self.assertEqual(self.create(starts_on="2026-12-10", ends_on="2026-12-01").status_code, 400)
        self.assertEqual(self.create(colour="red").status_code, 400)

    def test_the_portal_shows_switched_on_ads_within_their_dates_and_counts_views_and_taps(self):
        today = timezone.localdate()
        on = self.create(title="Phones at Abel's", advertiser="Abel Phones", link="https://abel.example").data
        self.create(title="Switched off", active=False)
        self.create(title="Over", ends_on=(today - datetime.timedelta(days=1)).isoformat())
        self.create(title="Later", starts_on=(today + datetime.timedelta(days=3)).isoformat())
        film = self.create(title="New this week", film=str(self.film.id)).data
        shown = self.portal_ads()
        self.assertEqual({a["title"] for a in shown}, {"Phones at Abel's", "New this week"})
        self.assertNotIn("views", shown[0])  # counts are the owner's
        tap = APIClient().post(f"/api/v1/portal/{self.shop.id}/ads/{on['id']}/tap/", **HEADER).data
        self.assertEqual(tap, {"film": None, "link": "https://abel.example"})
        self.assertEqual(
            APIClient().post(f"/api/v1/portal/{self.shop.id}/ads/{film['id']}/tap/", **HEADER).data["film"],
            str(self.film.id),
        )
        ad = Ad.objects.get(id=on["id"])
        self.assertEqual((ad.views, ad.taps), (1, 1))
        hidden = Ad.objects.get(title="Switched off")
        r = APIClient().post(f"/api/v1/portal/{self.shop.id}/ads/{hidden.id}/tap/", **HEADER)
        self.assertEqual(r.status_code, 404)
        listed = {a["title"]: a for a in self.client.get(f"/api/v1/movie-shops/{self.shop.id}/ads/").data}
        self.assertEqual((listed["Over"]["showing"], listed["Phones at Abel's"]["showing"]), (False, True))

    def test_a_closed_portal_shows_no_ads(self):
        self.create()
        self.client.put(f"/api/v1/movie-shops/{self.shop.id}/portal/", {"portal_open": False}, format="json")
        self.assertEqual(APIClient().get(f"/api/v1/portal/{self.shop.id}/ads/").status_code, 404)

    def test_pictures_must_be_real_pictures_and_are_served_on_the_portal(self):
        ad = self.create().data
        url = f"/api/v1/movie-ads/{ad['id']}/picture/"
        fake = SimpleUploadedFile("x.png", b"<html>not a picture</html>", content_type="image/png")
        self.assertEqual(self.client.post(url, {"file": fake}, format="multipart").status_code, 400)
        real = SimpleUploadedFile("x.png", png(), content_type="image/png")
        r = self.client.post(url, {"file": real}, format="multipart")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data["has_picture"])
        served = APIClient().get(f"/api/v1/portal/{self.shop.id}/ads/{ad['id']}/picture/")
        self.assertEqual((served.status_code, served["Content-Type"]), (200, "image/png"))
        self.assertEqual(b"".join(served) if hasattr(served, "streaming_content") else served.content, png())
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(io.BytesIO(png()).read(4), b"\x89PNG")

    def test_editing_deleting_and_the_limit(self):
        ad = self.create().data
        r = self.client.patch(
            f"/api/v1/movie-ads/{ad['id']}/", {"active": False, "position": 3}, format="json"
        )
        self.assertEqual((r.data["active"], r.data["position"], r.data["showing"]), (False, 3, False))
        self.assertEqual(self.client.delete(f"/api/v1/movie-ads/{ad['id']}/").status_code, 204)
        self.assertFalse(Ad.objects.exists())
        Ad.objects.bulk_create([Ad(shop=self.shop, title=f"Ad {i}") for i in range(50)])
        self.assertEqual(self.create().status_code, 400)

    def test_a_film_ad_opens_the_film_for_a_signed_in_customer_only(self):
        from django.core.cache import cache

        cache.clear()
        customer = APIClient()
        r = customer.post(
            f"/api/v1/portal/{self.shop.id}/signup/",
            {"name": "Hana", "phone": "0944000000", "password": "Portal-pass-2026"},
            format="json",
            **HEADER,
        )
        self.assertEqual(r.status_code, 201, r.data)
        url = f"/api/v1/portal/{self.shop.id}/titles/{self.film.id}/"
        self.assertEqual(customer.get(url).data["title"], "Desert Wind")
        self.assertNotIn("relative_path", customer.get(url).data)
        self.assertEqual(APIClient().get(url).status_code, 401)
        self.film.hidden = True
        self.film.save()
        self.assertEqual(customer.get(url).status_code, 404)
