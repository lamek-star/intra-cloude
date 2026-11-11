"""Movie Shop phase 2 (ADR-0022): counter sales, the IF Pay payment request, cash, and the copy jobs the
media agent carries out. Pay itself is not part of this test stack: the Pay bridge is replaced by a stand-in
that answers the way Pay does (pending, paid with a receipt, expired)."""

from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from app_platform.tests.test_foundation import project_for
from movie_shop.models import MovieShop, Sale, Title
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission

PAY = "movie_shop.sales.pay_bridge"
REPORT = {
    "computer": "SHOP-PC",
    "drives": [
        {
            "root": "D:\\",
            "label": "Movies",
            "kind": "fixed",
            "total_bytes": 4 * 10**12,
            "free_bytes": 10**12,
            "folders": [],
        },
        {
            "root": "E:\\",
            "label": "KINGSTON",
            "kind": "removable",
            "total_bytes": 64 * 10**9,
            "free_bytes": 10 * 10**9,
            "folders": [],
        },
    ],
}


class SaleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="sales-owner@example.com")
        cls.org = create_organization(name="Sales Movies", created_by=cls.owner)
        cls.project = project_for(cls.owner, cls.org)
        cls.clerk = User.objects.create_user(email="sales-clerk@example.com")
        Membership.objects.create(user=cls.clerk, organization=cls.org, status=Membership.Status.ACTIVE)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.owner)
        data = self.client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Lamek: Movies?", "project": str(self.project.id)},
            format="json",
        ).data
        self.shop = MovieShop.objects.get(pk=data["id"])
        token = self.client.post(f"/api/v1/movie-shops/{self.shop.id}/agent-credential/").data["token"]
        self.agent = APIClient()
        self.agent.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.agent.post("/api/v1/movie-agent/report/", REPORT, format="json")
        lib = self.client.post(
            f"/api/v1/movie-shops/{self.shop.id}/libraries/", {"path": "D:\\Movies"}, format="json"
        ).data
        gen = self.agent.post(
            f"/api/v1/movie-agent/libraries/{lib['id']}/scan/start/", {}, format="json"
        ).data["generation"]
        self.agent.post(
            f"/api/v1/movie-agent/libraries/{lib['id']}/scan/titles/",
            {
                "generation": gen,
                "titles": [
                    {
                        "relative_path": "Action\\Desert Wind (2025).mp4",
                        "category": "Action",
                        "title": "Desert Wind",
                        "size_bytes": 2 * 10**9,
                    },
                    {
                        "relative_path": "Series\\The Coffee House",
                        "category": "Series",
                        "title": "The Coffee House",
                        "kind": "series",
                        "episodes": 10,
                        "size_bytes": 5 * 10**9,
                    },
                ],
            },
            format="json",
        )
        self.agent.post(
            f"/api/v1/movie-agent/libraries/{lib['id']}/scan/finish/", {"generation": gen}, format="json"
        )
        self.client.put(
            f"/api/v1/movie-shops/{self.shop.id}/prices/",
            {"default_price": 50, "categories": {"Series": 60}},
            format="json",
        )
        self.titles = {t.title: str(t.id) for t in Title.objects.all()}

    def sell(self, method="cash", destination="E:\\", titles=None, client=None):
        return (client or self.client).post(
            f"/api/v1/movie-shops/{self.shop.id}/sales/",
            {
                "titles": titles or list(self.titles.values()),
                "destination": destination,
                "method": method,
                "customer_name": "Selam",
            },
            format="json",
        )

    def test_a_cash_sale_is_copied_by_the_agent_into_a_folder_named_after_the_shop(self):
        sale = self.sell().data
        self.assertEqual(sale["total"], 110)  # 50 + 60
        self.assertEqual(sale["status"], "awaiting_payment")
        self.assertEqual(
            self.agent.post("/api/v1/movie-agent/report/", REPORT, format="json").data["copies"], []
        )  # not paid yet
        paid = self.client.post(f"/api/v1/movie-sales/{sale['id']}/cash/").data
        self.assertEqual((paid["status"], paid["method"]), ("paid", "cash"))
        work = self.agent.post("/api/v1/movie-agent/report/", REPORT, format="json").data
        self.assertEqual(work["poll_seconds"], 2)
        copies = {c["relative_path"]: c for c in work["copies"]}
        desert = copies["Action\\Desert Wind (2025).mp4"]
        self.assertEqual(
            (desert["library"], desert["destination"], desert["folder"]),
            ("D:\\Movies", "E:\\", "Lamek Movies\\Action"),
        )
        for c in work["copies"]:
            self.agent.post(
                f"/api/v1/movie-agent/copies/{c['line']}/",
                {"status": "copying", "copied_bytes": 10},
                format="json",
            )
            done = self.agent.post(
                f"/api/v1/movie-agent/copies/{c['line']}/",
                {"status": "copied", "copied_bytes": c["size_bytes"]},
                format="json",
            )
            self.assertEqual(done.status_code, 200, done.data)
        self.assertEqual(self.client.get(f"/api/v1/movie-sales/{sale['id']}/").data["status"], "done")
        self.assertEqual(
            self.agent.post("/api/v1/movie-agent/report/", REPORT, format="json").data["copies"], []
        )

    def test_an_ifpay_sale_asks_pay_and_starts_copying_only_once_pay_says_paid(self):
        with mock.patch(PAY) as pay:
            pay.create_request.return_value = {
                "id": "6f1c1c4e-2b3a-4c1d-9e2f-0123456789ab",
                "code": "4821",
                "qr_svg": "<svg/>",
                "expires_at": "2026-11-10T12:10:00+00:00",
            }
            pay.request_status.return_value = {"status": "pending"}
            sale = self.sell(method="ifpay").data
            kwargs = pay.create_request.call_args.kwargs
            self.assertEqual(
                (kwargs["amount_minor"], kwargs["external_id"], kwargs["actor_id"]),
                (11000, sale["number"], self.owner.pk),
            )
            self.assertEqual(sale["pay"]["code"], "4821")
            self.assertEqual(
                self.client.get(f"/api/v1/movie-sales/{sale['id']}/").data["status"], "awaiting_payment"
            )
            pay.request_status.return_value = {"status": "paid", "receipt_number": "RCP-20261110-0187"}
            paid = self.client.get(f"/api/v1/movie-sales/{sale['id']}/").data
        self.assertEqual((paid["status"], paid["receipt_number"]), ("paid", "RCP-20261110-0187"))
        self.assertIsNone(paid["pay"])
        self.assertEqual(
            len(self.agent.post("/api/v1/movie-agent/report/", REPORT, format="json").data["copies"]), 2
        )

    def test_an_expired_payment_cancels_the_sale(self):
        with mock.patch(PAY) as pay:
            pay.create_request.return_value = {
                "id": "6f1c1c4e-2b3a-4c1d-9e2f-0123456789ab",
                "code": "1",
                "qr_svg": "",
                "expires_at": None,
            }
            sale = self.sell(method="ifpay").data
            pay.request_status.return_value = {"status": "expired"}
            self.assertEqual(
                self.client.get(f"/api/v1/movie-sales/{sale['id']}/").data["status"], "cancelled"
            )

    def test_selling_needs_movies_sell(self):
        clerk = APIClient()
        clerk.force_login(self.clerk)
        grant_resource_permission(
            user=self.clerk,
            organization_id=self.org.id,
            permission_code="movies.read",
            resource_type="movie_shop",
            resource_id=str(self.shop.id),
            granted_by=self.owner,
        )
        self.assertEqual(self.sell(client=clerk).status_code, 403)
        grant_resource_permission(
            user=self.clerk,
            organization_id=self.org.id,
            permission_code="movies.sell",
            resource_type="movie_shop",
            resource_id=str(self.shop.id),
            granted_by=self.owner,
        )
        self.assertEqual(self.sell(client=clerk).status_code, 201)

    def test_the_destination_must_be_a_customer_drive_the_agent_sees(self):
        self.assertEqual(self.sell(destination="F:\\").status_code, 400)  # not plugged in
        self.assertEqual(self.sell(destination="D:\\").status_code, 400)  # the library's own disk
        self.assertEqual(self.sell(destination="..\\x").status_code, 400)

    def test_hidden_or_foreign_titles_and_a_full_drive_are_refused(self):
        desert = Title.objects.get(title="Desert Wind")
        desert.hidden = True
        desert.save()
        self.assertEqual(self.sell(titles=[str(desert.id)]).status_code, 400)
        self.assertEqual(self.sell(titles=["6f1c1c4e-2b3a-4c1d-9e2f-0123456789ab"]).status_code, 400)
        small = {**REPORT, "drives": [REPORT["drives"][0], {**REPORT["drives"][1], "free_bytes": 10**6}]}
        self.agent.post("/api/v1/movie-agent/report/", small, format="json")
        self.assertEqual(self.sell(titles=[self.titles["The Coffee House"]]).status_code, 400)

    def test_nothing_is_copied_for_an_unpaid_or_cancelled_sale_and_only_this_shops_agent_reports_progress(
        self,
    ):
        sale = self.sell().data
        line = sale["lines"][0]["id"]
        self.assertEqual(
            self.agent.post(
                f"/api/v1/movie-agent/copies/{line}/", {"status": "copied"}, format="json"
            ).status_code,
            400,
        )
        self.client.post(f"/api/v1/movie-sales/{sale['id']}/cancel/")
        self.assertEqual(Sale.objects.get().status, "cancelled")
        self.assertEqual(self.client.post(f"/api/v1/movie-sales/{sale['id']}/cash/").status_code, 400)
        other = self.client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Second", "project": str(self.project.id)},
            format="json",
        ).data
        token = self.client.post(f"/api/v1/movie-shops/{other['id']}/agent-credential/").data["token"]
        agent2 = APIClient()
        agent2.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(
            agent2.post(
                f"/api/v1/movie-agent/copies/{line}/", {"status": "copying"}, format="json"
            ).status_code,
            404,
        )

    def test_a_failed_copy_can_be_tried_again(self):
        sale = self.sell().data
        self.client.post(f"/api/v1/movie-sales/{sale['id']}/cash/")
        line = sale["lines"][0]["id"]
        self.agent.post(
            f"/api/v1/movie-agent/copies/{line}/",
            {"status": "failed", "message": "The drive was removed."},
            format="json",
        )
        again = self.client.post(f"/api/v1/movie-sales/{sale['id']}/retry/").data
        self.assertEqual({ln["copy_status"] for ln in again["lines"]}, {"waiting"})
