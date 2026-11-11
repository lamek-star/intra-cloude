"""Movie Shop phase 3 (ADR-0022): the customer portal -- sign-up and sign-in with the portal's own cookie, the
owner adding a customer to IF Pay, orders the counter charges, and Movie Shop points. IF Pay itself is not
part of this test stack: the Pay bridge is replaced by a stand-in that answers the way Pay's internal API
does."""

import datetime
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from app_platform.tests.test_foundation import project_for
from movie_shop.models import MovieShop, PointsEntry, PortalCustomer, Sale, Title
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission

PAY = "movie_shop.portal.pay_bridge"
SALES_PAY = "movie_shop.sales.pay_bridge"
HEADER = {"HTTP_X_PORTAL_REQUEST": "1"}
PASSWORD = "Portal-pass-2026"
REPORT = {
    "computer": "SHOP-PC",
    "drives": [
        {"root": "D:\\", "label": "Movies", "kind": "fixed", "total_bytes": 4 * 10**12, "free_bytes": 10**12},
        {
            "root": "E:\\",
            "label": "USB",
            "kind": "removable",
            "total_bytes": 64 * 10**9,
            "free_bytes": 10 * 10**9,
        },
    ],
}


def wallet(created=True, external="x"):
    return {
        "id": "6f1c1c4e-2b3a-4c1d-9e2f-0123456789ab",
        "username": "selam",
        "display_name": "Selam",
        "active": True,
        "must_change_password": True,
        "balance_minor": 0,
        "wallet_path": "/apps/pay-1/wallet",
        "created": created,
        "first_password": "k7mq-x2vd-9tna" if created else None,
    }


class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="portal-owner@example.com")
        cls.org = create_organization(name="Portal Movies", created_by=cls.owner)
        cls.project = project_for(cls.owner, cls.org)
        cls.clerk = User.objects.create_user(email="portal-clerk@example.com")
        Membership.objects.create(user=cls.clerk, organization=cls.org, status=Membership.Status.ACTIVE)
        cls.outsider = User.objects.create_user(email="portal-outsider@example.com")
        create_organization(name="Other Shop", created_by=cls.outsider)

    def setUp(self):
        cache.clear()  # the "auth" throttle scope is 10/minute per client
        self.owner_client = APIClient()
        self.owner_client.force_login(self.owner)
        data = self.owner_client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Lamek Movies", "project": str(self.project.id)},
            format="json",
        ).data
        self.shop = MovieShop.objects.get(pk=data["id"])
        token = self.owner_client.post(f"/api/v1/movie-shops/{self.shop.id}/agent-credential/").data["token"]
        self.agent = APIClient()
        self.agent.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.agent.post("/api/v1/movie-agent/report/", REPORT, format="json")
        lib = self.owner_client.post(
            f"/api/v1/movie-shops/{self.shop.id}/libraries/", {"path": "D:\\Movies"}, format="json"
        ).data
        gen = self.agent.post(
            f"/api/v1/movie-agent/libraries/{lib['id']}/scan/start/", {}, format="json"
        ).data["generation"]
        titles = [
            {
                "relative_path": f"Action\\Film {i}.mp4",
                "category": "Action",
                "title": f"Film {i}",
                "size_bytes": 10**9,
            }
            for i in range(1, 6)
        ]
        self.agent.post(
            f"/api/v1/movie-agent/libraries/{lib['id']}/scan/titles/",
            {"generation": gen, "titles": titles},
            format="json",
        )
        self.agent.post(
            f"/api/v1/movie-agent/libraries/{lib['id']}/scan/finish/", {"generation": gen}, format="json"
        )
        self.owner_client.put(
            f"/api/v1/movie-shops/{self.shop.id}/prices/",
            {"default_price": 40, "categories": {}},
            format="json",
        )
        Title.objects.filter(title="Film 5").update(price=20)
        self.titles = {t.title: str(t.id) for t in Title.objects.all()}
        self.open_portal(welcome_points=30, referral_points=15, every_nth_free=3)

    # ---- helpers -------------------------------------------------------------------------------------------
    def open_portal(self, **rules):
        r = self.owner_client.put(
            f"/api/v1/movie-shops/{self.shop.id}/portal/", {"portal_open": True, **rules}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.data)

    def url(self, path="", shop=None):
        return f"/api/v1/portal/{shop or self.shop.id}/{path}"

    def sign_up(self, phone="0911 22 33 44", name="Selam", **extra):
        client = APIClient()
        r = client.post(
            self.url("signup/"),
            {"name": name, "phone": phone, "password": PASSWORD, **extra},
            format="json",
            **HEADER,
        )
        return client, r

    def approve(self, customer_id, created=True):
        with mock.patch(PAY) as pay:
            pay.open_customer_wallet.return_value = wallet(created)
            r = self.owner_client.post(f"/api/v1/movie-customers/{customer_id}/approve/")
        return r, pay

    def approved_customer(self, phone="0911223344", name="Selam"):
        client, r = self.sign_up(phone=phone, name=name)
        self.approve(r.data["id"])
        return client, r.data["id"]

    # ---- the portal itself ---------------------------------------------------------------------------------
    def test_a_closed_portal_does_not_exist_and_only_movies_manage_opens_it(self):
        self.owner_client.put(
            f"/api/v1/movie-shops/{self.shop.id}/portal/", {"portal_open": False}, format="json"
        )
        self.assertEqual(APIClient().get(self.url()).status_code, 404)
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
        r = clerk.put(f"/api/v1/movie-shops/{self.shop.id}/portal/", {"portal_open": True}, format="json")
        self.assertEqual(r.status_code, 403)
        self.open_portal()
        home = APIClient().get(self.url()).data
        self.assertEqual((home["shop"]["name"], home["customer"]), ("Lamek Movies", None))
        self.assertEqual(home["shop"]["rules"]["every_nth_free"], 3)

    def test_sign_up_sets_an_httponly_strict_cookie_on_the_portal_api_only(self):
        client, r = self.sign_up()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["status"], r.data["phone"]), ("pending", "0911223344"))
        cookie = r.cookies["ifportal"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual((cookie["samesite"], cookie["path"]), ("Strict", "/api/v1/portal/"))
        self.assertEqual(client.get(self.url("me/")).data["name"], "Selam")
        stored = PortalCustomer.objects.get()
        self.assertNotIn(PASSWORD, stored.password)

    def test_sign_up_rules(self):
        self.assertEqual(self.sign_up(phone="12")[1].status_code, 400)
        weak = APIClient().post(
            self.url("signup/"),
            {"name": "A", "phone": "0911000000", "password": "123"},
            format="json",
            **HEADER,
        )
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(self.sign_up()[1].status_code, 201)
        self.assertEqual(self.sign_up(phone="+0911223344".lstrip("+"))[1].status_code, 400)  # same phone
        self.assertEqual(self.sign_up(phone="0922000000", referral_code="NOPE12")[1].status_code, 400)

    def test_a_change_without_the_portal_header_is_refused(self):
        r = APIClient().post(
            self.url("signup/"), {"name": "Selam", "phone": "0911223344", "password": PASSWORD}, format="json"
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(PortalCustomer.objects.exists())

    def test_sign_in_and_out(self):
        self.sign_up()
        client = APIClient()
        bad = client.post(
            self.url("login/"), {"phone": "0911223344", "password": "wrong"}, format="json", **HEADER
        )
        self.assertEqual(bad.status_code, 401)
        unknown = client.post(
            self.url("login/"), {"phone": "0999999999", "password": PASSWORD}, format="json", **HEADER
        )
        self.assertEqual(unknown.status_code, 401)
        ok = client.post(
            self.url("login/"), {"phone": "0911-22-33-44", "password": PASSWORD}, format="json", **HEADER
        )
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(client.get(self.url("me/")).status_code, 200)
        client.post(self.url("logout/"), **HEADER)
        self.assertEqual(client.get(self.url("me/")).status_code, 401)

    def test_sign_in_is_rate_limited(self):
        self.sign_up()
        codes = [
            APIClient()
            .post(self.url("login/"), {"phone": "0911223344", "password": "wrong"}, format="json", **HEADER)
            .status_code
            for _ in range(11)
        ]
        self.assertEqual(codes[-1], 429)

    def test_customers_of_one_shop_are_unknown_at_another(self):
        other = self.owner_client.post(
            f"/api/v1/organizations/{self.org.id}/movie-shops/",
            {"name": "Second Shop", "project": str(self.project.id)},
            format="json",
        ).data
        MovieShop.objects.filter(id=other["id"]).update(portal_open=True)
        client, _ = self.sign_up()
        self.assertEqual(client.get(self.url("me/", shop=other["id"])).status_code, 401)
        self.assertEqual(client.get(self.url("titles/", shop=other["id"])).status_code, 401)

    def test_a_waiting_customer_browses_but_cannot_order_and_never_sees_paths(self):
        client, _ = self.sign_up()
        page = client.get(self.url("titles/")).data
        self.assertEqual(page["count"], 5)
        self.assertNotIn("relative_path", page["results"][0])
        self.assertEqual(client.get(self.url("categories/")).data, [{"name": "Action", "count": 5}])
        r = client.post(self.url("orders/"), {"titles": [self.titles["Film 1"]]}, format="json", **HEADER)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(APIClient().get(self.url("titles/")).status_code, 401)

    # ---- the owner -----------------------------------------------------------------------------------------
    def test_approving_adds_the_customer_to_if_pay_once_and_gives_the_welcome_and_referral_points(self):
        _, first = self.approved_customer()
        referrer = PortalCustomer.objects.get(id=first)
        client, r = self.sign_up(phone="0922000000", name="Abel", referral_code=referrer.referral_code)
        approve, pay = self.approve(r.data["id"])
        self.assertEqual(approve.status_code, 200, approve.data)
        self.assertEqual(approve.data["wallet"]["first_password"], "k7mq-x2vd-9tna")
        kwargs = pay.open_customer_wallet.call_args.kwargs
        self.assertEqual(
            (kwargs["actor_id"], kwargs["external_id"]), (self.owner.pk, f"movie-customer:{r.data['id']}")
        )
        self.assertEqual(kwargs["username"], "abel")
        me = client.get(self.url("me/")).data
        self.assertEqual((me["status"], me["points"]), ("approved", 30))
        self.assertEqual(PortalCustomer.objects.get(id=first).points.filter(reason="referral").count(), 1)
        # Approving again (the same wallet, no password) gives nothing twice.
        again, _ = self.approve(r.data["id"], created=False)
        self.assertIsNone(again.data["wallet"]["first_password"])
        self.assertEqual(PointsEntry.objects.filter(customer_id=r.data["id"], reason="welcome").count(), 1)
        self.assertNotIn("k7mq", str(PortalCustomer.objects.get(id=r.data["id"]).__dict__))

    def test_customers_need_movies_manage_and_stay_in_their_organization(self):
        _, r = self.sign_up()
        clerk = APIClient()
        clerk.force_login(self.clerk)
        self.assertEqual(clerk.get(f"/api/v1/movie-shops/{self.shop.id}/customers/").status_code, 403)
        self.assertEqual(clerk.post(f"/api/v1/movie-customers/{r.data['id']}/approve/").status_code, 403)
        outsider = APIClient()
        outsider.force_login(self.outsider)
        self.assertEqual(outsider.get(f"/api/v1/movie-shops/{self.shop.id}/customers/").status_code, 404)
        self.assertEqual(outsider.post(f"/api/v1/movie-customers/{r.data['id']}/approve/").status_code, 404)
        listed = self.owner_client.get(f"/api/v1/movie-shops/{self.shop.id}/customers/?status=pending").data
        self.assertEqual(listed["count"], 1)

    def test_blocking_signs_the_customer_out_and_cancels_their_orders(self):
        client, cid = self.approved_customer()
        client.post(
            self.url("orders/"),
            {"titles": [self.titles["Film 1"]], "use_points": True},
            format="json",
            **HEADER,
        )
        self.owner_client.post(f"/api/v1/movie-customers/{cid}/block/")
        self.assertEqual(client.get(self.url("me/")).status_code, 401)
        self.assertEqual(Sale.objects.get().status, "cancelled")
        login = APIClient().post(
            self.url("login/"), {"phone": "0911223344", "password": PASSWORD}, format="json", **HEADER
        )
        self.assertEqual(login.status_code, 401)
        self.owner_client.post(f"/api/v1/movie-customers/{cid}/unblock/")
        self.assertEqual(PortalCustomer.objects.get(id=cid).status, "approved")

    # ---- orders and rewards --------------------------------------------------------------------------------
    def charge(self, sale_id, method="cash"):
        return self.owner_client.post(
            f"/api/v1/movie-sales/{sale_id}/charge/", {"destination": "E:\\", "method": method}, format="json"
        )

    def test_an_order_is_charged_at_the_counter_with_points_then_every_third_title_is_free(self):
        client, cid = self.approved_customer()
        preview = client.post(
            self.url("orders/"),
            {"titles": [self.titles["Film 1"], self.titles["Film 2"]], "use_points": True, "preview": True},
            format="json",
            **HEADER,
        ).data
        self.assertEqual((preview["subtotal"], preview["points_used"], preview["total"]), (80, 30, 50))
        order = client.post(
            self.url("orders/"),
            {"titles": [self.titles["Film 1"], self.titles["Film 2"]], "use_points": True},
            format="json",
            **HEADER,
        ).data
        self.assertEqual(order["status"], "ordered")
        listed = self.owner_client.get(f"/api/v1/movie-shops/{self.shop.id}/sales/?status=ordered").data
        self.assertEqual(listed["results"][0]["customer"]["name"], "Selam")
        charged = self.charge(order["id"]).data
        self.assertEqual(
            (charged["status"], charged["total"], charged["points_used"]), ("awaiting_payment", 50, 30)
        )
        self.assertEqual(client.get(self.url("me/")).data["points"], 0)
        self.owner_client.post(f"/api/v1/movie-sales/{order['id']}/cash/")
        # The third title: free (the customer's 3rd), so nothing to pay and paid at once.
        second = client.post(
            self.url("orders/"), {"titles": [self.titles["Film 3"]]}, format="json", **HEADER
        ).data
        done = self.charge(second["id"]).data
        self.assertEqual((done["status"], done["total"], done["discount"]), ("paid", 0, 40))
        self.assertTrue(done["lines"][0]["free"])

    def test_the_cheapest_title_in_the_cart_is_the_free_one(self):
        client, _ = self.approved_customer()
        ids = [self.titles[n] for n in ("Film 1", "Film 2", "Film 5")]  # 40, 40, 20
        order = client.post(self.url("orders/"), {"titles": ids}, format="json", **HEADER).data
        charged = self.charge(order["id"]).data
        self.assertEqual((charged["total"], charged["discount"]), (80, 20))
        self.assertEqual([ln["title"] for ln in charged["lines"] if ln["free"]], ["Film 5"])

    def test_a_cancelled_sale_gives_the_points_back_and_an_order_is_charged_once(self):
        client, _ = self.approved_customer()
        order = client.post(
            self.url("orders/"),
            {"titles": [self.titles["Film 1"]], "use_points": True},
            format="json",
            **HEADER,
        ).data
        self.charge(order["id"])
        self.assertEqual(self.charge(order["id"]).status_code, 400)
        self.assertEqual(client.get(self.url("me/")).data["points"], 0)
        self.owner_client.post(f"/api/v1/movie-sales/{order['id']}/cancel/")
        self.assertEqual(client.get(self.url("me/")).data["points"], 30)

    def test_an_expired_if_pay_request_gives_the_points_back(self):
        client, _ = self.approved_customer()
        order = client.post(
            self.url("orders/"),
            {"titles": [self.titles["Film 1"]], "use_points": True},
            format="json",
            **HEADER,
        ).data
        with mock.patch(SALES_PAY) as pay:
            pay.create_request.return_value = {
                "id": "6f1c1c4e-2b3a-4c1d-9e2f-0123456789ab",
                "code": "c",
                "qr_svg": "",
            }
            self.charge(order["id"], method="ifpay")
            pay.request_status.return_value = {"status": "expired"}
            self.owner_client.get(f"/api/v1/movie-sales/{order['id']}/")
        self.assertEqual(Sale.objects.get(id=order["id"]).status, "cancelled")
        self.assertEqual(client.get(self.url("me/")).data["points"], 30)

    def test_customers_cancel_only_their_own_waiting_orders_and_have_at_most_three(self):
        client, _ = self.approved_customer()
        other, _ = self.approved_customer(phone="0933000000", name="Hana")
        orders = [
            client.post(self.url("orders/"), {"titles": [self.titles["Film 1"]]}, format="json", **HEADER)
            for _ in range(4)
        ]
        self.assertEqual([o.status_code for o in orders], [201, 201, 201, 400])
        first = orders[0].data["id"]
        self.assertEqual(other.post(self.url(f"orders/{first}/cancel/"), **HEADER).status_code, 404)
        self.assertEqual(
            client.post(self.url(f"orders/{first}/cancel/"), **HEADER).data["status"], "cancelled"
        )

    def test_birthday_points_once_a_year_in_the_birthday_month(self):
        self.open_portal(birthday_points=25)
        today = timezone.localdate()
        client, r = self.sign_up(birthday=datetime.date(1995, today.month, 1).isoformat())
        self.approve(r.data["id"])
        self.assertEqual(client.get(self.url("me/")).data["points"], 55)  # 30 welcome + 25 birthday
        self.assertEqual(client.get(self.url("me/")).data["points"], 55)

    def test_the_wallet_balance_comes_from_if_pay(self):
        client, _ = self.approved_customer()
        with mock.patch(PAY) as pay:
            pay.customer_wallet.return_value = {
                **wallet(),
                "balance_minor": 12345,
                "must_change_password": False,
            }
            me = client.get(self.url("me/")).data
        self.assertEqual((me["wallet"]["username"], me["wallet"]["balance"]), ("selam", 123.45))
