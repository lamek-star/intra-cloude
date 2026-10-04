"""Business-operation authority over stock (ADR-0017): MAY SELL is not MAY RECEIVE, and neither is
MAY MOVE STOCK.

The authorization matrix, the direct-movement bypass, revocation, cross-organization and wrong-application
attempts, the ledger's own refusal of an oversell despite full authority, and the existing
per-model restrictions
that must keep applying underneath the operation authority.
"""

import datetime

from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, templates
from app_platform.tests.test_foundation import sample
from app_platform.tests.test_quantity_ledger import _LedgerFixture
from app_platform.tests.test_transactions import TransactionBase
from audit.models import AuditEvent
from organizations.models import Membership

SELL_MODELS = ("sales_order", "sales_order_line", "invoice")
RECEIVE_MODELS = ("purchase_order", "purchase_order_line")


def stamp(delta=datetime.timedelta()):
    return (datetime.datetime.now(datetime.UTC) + delta).strftime("%Y-%m-%dT%H:%M:%S")


class OperationBase(TransactionBase):
    def setUp(self):
        super().setUp()
        self._receive(50)  # the owner (an organization administrator) holds every inventory authority
        self.supplier = self._create("supplier", name="Acme Supply")

    # -- people and grants ----------------------------------------------------------------------
    def _member(self, email):
        user = User.objects.create_user(email=email)
        Membership.objects.create(user=user, organization=self.org, status=Membership.Status.ACTIVE)
        client = APIClient()
        client.force_authenticate(user)
        return user, client

    def _share(self, user, resource_type, resource_id, level):
        response = self.client.post(
            reverse("share-grant-list-create", args=[self.org.id]),
            {
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "principal_type": "user",
                "user_id": str(user.id),
                "level": level,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def _authority(self, user, level):
        return self._share(user, "inventory_operations", self.instance.id, level)

    def _model_access(self, user, keys, level="write"):
        for key in keys:
            self._share(user, "app_model", self.models[key].id, level)

    def _seller(self, email="seller@example.com"):
        user, client = self._member(email)
        self._model_access(user, SELL_MODELS)
        self._authority(user, "sell")
        return user, client

    def _receiver(self, email="receiver@example.com"):
        user, client = self._member(email)
        self._model_access(user, RECEIVE_MODELS)
        self._authority(user, "receive")
        return user, client

    # -- the two operations ---------------------------------------------------------------------
    def _operation(self, client, name, body, key="key-1"):
        extra = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return client.post(
            f"/api/v1/app-instances/{self.instance.id}/operations/{name}/", body, format="json", **extra
        )

    def _sale_body(self, quantity=1, invoice="INV-T-1", **overrides):
        body = {
            "customer": str(self.customer["id"]),
            "invoice_number": invoice,
            "occurred_at": stamp(),
            "lines": [
                {
                    "part": str(self.part["id"]),
                    "warehouse": str(self.warehouse["id"]),
                    "quantity": quantity,
                    "unit_price": "15.00",
                }
            ],
        }
        body.update(overrides)
        return body

    def _receive_body(self, quantity=5, **overrides):
        body = {
            "part": str(self.part["id"]),
            "warehouse": str(self.warehouse["id"]),
            "quantity": quantity,
            "occurred_at": stamp(),
        }
        body.update(overrides)
        return body

    def _sell(self, client, quantity=1, invoice="INV-T-1", key="sell-1", **overrides):
        return self._operation(client, "sell", self._sale_body(quantity, invoice, **overrides), key)

    def _receive_op(self, client, quantity=5, key="recv-1", **overrides):
        return self._operation(client, "receive", self._receive_body(quantity, **overrides), key)

    def _counts(self):
        return {key: len(self._records(key)) for key in (*SELL_MODELS, "stock_movement", *RECEIVE_MODELS)}

    def _movement_payload(self, delta, kind):
        return self._payload(
            "stock_movement",
            stock_movement_part=self.part["id"],
            stock_movement_warehouse=self.warehouse["id"],
            quantity_delta=delta,
            movement_type=kind,
        )


class AuthorizationMatrixTests(OperationBase):
    def test_no_authority_can_neither_sell_nor_receive(self):
        user, client = self._member("nobody@example.com")
        self._model_access(
            user, SELL_MODELS + RECEIVE_MODELS
        )  # module access alone is not operation authority
        before = self._counts()
        self.assertEqual(self._sell(client).status_code, 403)
        self.assertEqual(self._receive_op(client).status_code, 403)
        self.assertEqual(self._counts(), before)
        self.assertEqual(self._balance(), 50)

    def test_sell_only_may_sell_and_may_not_receive(self):
        _, client = self._seller()
        sold = self._sell(client, quantity=3)
        self.assertEqual(sold.status_code, 201, sold.data)
        self.assertEqual(self._balance(), 47)
        denied = self._receive_op(client)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertEqual(self._balance(), 47)

    def test_receive_only_may_receive_and_may_not_sell(self):
        _, client = self._receiver()
        received = self._receive_op(client, quantity=10)
        self.assertEqual(received.status_code, 201, received.data)
        self.assertEqual(self._balance(), 60)
        before = self._counts()
        denied = self._sell(client)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertEqual(self._counts(), before)
        self.assertEqual(self._balance(), 60)

    def test_a_deliberately_combined_role_may_do_both(self):
        user, client = self._member("both@example.com")
        self._model_access(user, SELL_MODELS)
        self._authority(user, "sell")
        self._authority(user, "receive")
        self.assertEqual(self._sell(client, quantity=2).status_code, 201)
        self.assertEqual(self._receive_op(client, quantity=4).status_code, 201)
        self.assertEqual(self._balance(), 52)

    def test_an_organization_administrator_may_do_both(self):
        self.assertEqual(self._sell(self.client, quantity=1, key="admin-sell").status_code, 201)
        self.assertEqual(self._receive_op(self.client, quantity=1, key="admin-recv").status_code, 201)

    def test_adjust_and_transfer_imply_neither_sell_nor_receive(self):
        for level in ("adjust", "transfer"):
            user, client = self._member(f"{level}@example.com")
            self._model_access(user, SELL_MODELS + RECEIVE_MODELS)
            self._authority(user, level)
            self.assertEqual(self._sell(client, key=f"s-{level}").status_code, 403, level)
            self.assertEqual(self._receive_op(client, key=f"r-{level}").status_code, 403, level)

    def test_a_refusal_is_audited_against_the_actor_and_a_success_is_too(self):
        user, client = self._member("audited@example.com")
        self.assertEqual(self._sell(client).status_code, 403)
        denied = AuditEvent.objects.filter(
            actor=user, action="inventory.sell", result=AuditEvent.Result.DENIED
        )
        self.assertEqual(denied.count(), 1)
        self.assertEqual(denied.first().context["required"], "inventory.sell")
        seller, seller_client = self._seller("audited-seller@example.com")
        self.assertEqual(self._sell(seller_client, key="audited-1").status_code, 201)
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=seller, action="inventory.sell", result=AuditEvent.Result.SUCCESS
            ).exists()
        )


class RevocationTests(OperationBase):
    def test_revoking_sell_takes_effect_on_the_very_next_operation(self):
        user, client = self._member("revoked-seller@example.com")
        self._model_access(user, SELL_MODELS)
        share = self._authority(user, "sell")
        self.assertEqual(self._sell(client, key="r1", invoice="INV-R-1").status_code, 201)
        self.assertEqual(self.client.delete(reverse("share-grant-detail", args=[share])).status_code, 204)
        before = self._counts()
        self.assertEqual(self._sell(client, key="r2", invoice="INV-R-2").status_code, 403)
        self.assertEqual(self._counts(), before)

    def test_revoking_receive_takes_effect_on_the_very_next_operation(self):
        user, client = self._member("revoked-receiver@example.com")
        share = self._authority(user, "receive")
        self.assertEqual(self._receive_op(client, key="r1").status_code, 201)
        self.assertEqual(self.client.delete(reverse("share-grant-detail", args=[share])).status_code, 204)
        balance = self._balance()
        self.assertEqual(self._receive_op(client, key="r2").status_code, 403)
        self.assertEqual(self._balance(), balance)

    def test_revoking_sell_leaves_a_separately_granted_receive_intact(self):
        user, client = self._member("mixed@example.com")
        self._model_access(user, SELL_MODELS)
        sell_share = self._authority(user, "sell")
        self._authority(user, "receive")
        self.client.delete(reverse("share-grant-detail", args=[sell_share]))
        self.assertEqual(self._sell(client).status_code, 403)
        self.assertEqual(self._receive_op(client).status_code, 201)


class DirectMovementBypassTests(OperationBase):
    """Sale/receive authority is not authority to write the stock tables by hand, however the
    request is shaped."""

    def _stock_writer(self, level, email):
        user, client = self._member(email)
        self._model_access(user, SELL_MODELS + ("stock_movement", "inventory"))
        self._authority(user, level)
        return user, client

    def test_full_write_access_to_the_stock_tables_plus_sell_is_still_not_a_movement_right(self):
        _, client = self._stock_writer("sell", "bypass-sell@example.com")
        url = f"/api/v1/app-models/{self.models['stock_movement'].id}/records/"
        for delta, kind in ((5, "receive"), (-1, "sale"), (7, "adjustment")):
            response = client.post(url, self._movement_payload(delta, kind), format="json")
            self.assertEqual(response.status_code, 403, (delta, kind))
        self.assertEqual(self._balance(), 50)
        self.assertEqual(len(self._records("stock_movement")), 1)

    def test_the_generic_transaction_endpoint_is_no_way_round_it(self):
        _, client = self._stock_writer("receive", "bypass-tx@example.com")
        response = self._post(self._sale_ops(1), client=client)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(response.data["operation"], 2)  # the movement, after order and line
        self._assert_no_sale_documents()
        self.assertEqual(self._balance(), 50)

    def test_an_existing_movement_cannot_be_edited_or_deleted_by_an_operation_holder(self):
        _, client = self._stock_writer("sell", "bypass-edit@example.com")
        movement = self._records("stock_movement")[0]
        url = f"/api/v1/app-models/{self.models['stock_movement'].id}/records/{movement['id']}/"
        delta_field = self._definition_id("stock_movement", "quantity_delta")
        self.assertEqual(client.patch(url, {delta_field: 1000}, format="json").status_code, 403)
        self.assertEqual(client.delete(url).status_code, 403)
        self.assertEqual(self._balance(), 50)

    def test_an_adjuster_can_still_write_movements_directly_and_the_ledger_still_governs_them(self):
        user, client = self._member("adjuster@example.com")
        self._model_access(user, ("stock_movement", "inventory"))
        self._authority(user, "adjust")
        url = f"/api/v1/app-models/{self.models['stock_movement'].id}/records/"
        ok = client.post(url, self._movement_payload(4, "adjustment"), format="json")
        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(self._balance(), 54)
        too_far = client.post(url, self._movement_payload(-1000, "adjustment"), format="json")
        self.assertEqual(too_far.status_code, 400, too_far.data)  # the database, not authority, refuses it
        self.assertEqual(self._balance(), 54)

    def test_adjust_authority_without_module_access_to_the_stock_tables_is_refused(self):
        user, client = self._member("adjust-only@example.com")
        self._authority(user, "adjust")
        url = f"/api/v1/app-models/{self.models['stock_movement'].id}/records/"
        self.assertEqual(
            client.post(url, self._movement_payload(1, "adjustment"), format="json").status_code, 403
        )

    def test_a_request_cannot_name_its_own_operation(self):
        _, client = self._stock_writer("receive", "forge@example.com")
        url = f"/api/v1/app-models/{self.models['stock_movement'].id}/records/"
        forged = self._movement_payload(3, "receive")
        forged["movement_operation"] = "inventory.receive"
        self.assertEqual(client.post(url, forged, format="json").status_code, 403)
        via_query = client.post(
            url + "?movement_operation=inventory.receive", self._movement_payload(3, "receive"), format="json"
        )
        self.assertEqual(via_query.status_code, 403)
        self.assertEqual(self._balance(), 50)


class IsolationTests(OperationBase):
    def test_a_grant_on_one_application_is_no_authority_on_another(self):
        user, client = self._member("wrong-app@example.com")
        self._model_access(user, SELL_MODELS)
        other = instances.install(
            self.actor,
            self.project,
            {
                "label": "Other",
                "template_version": str(
                    templates.publish_template(
                        self.actor,
                        templates.create_template(
                            self.actor, self.org, {"label": "Other", "draft": sample()}
                        ),
                    ).id
                ),
            },
        )
        self._share(user, "inventory_operations", other.id, "sell")  # sell authority on the OTHER application
        self.assertEqual(self._sell(client).status_code, 403)  # ...is nothing on this one
        unsupported = client.post(
            f"/api/v1/app-instances/{other.id}/operations/sell/",
            self._sale_body(),
            format="json",
            HTTP_IDEMPOTENCY_KEY="other-1",
        )
        self.assertEqual(
            unsupported.status_code, 400, unsupported.data
        )  # authorized, but not a stock application

    def test_another_organizations_user_cannot_reach_the_operation_at_all(self):
        foreign = _LedgerFixture.build("ops-foreign@example.com", "Ops Foreign Org")
        try:
            response = self._sell(foreign.client)
            self.assertEqual(response.status_code, 404, response.data)
            self.assertEqual(self._receive_op(foreign.client).status_code, 404)
            self.assertEqual(self._balance(), 50)
        finally:
            foreign.drop_schema()

    def test_a_member_cannot_grant_themselves_operation_authority(self):
        user, client = self._member("self-grant@example.com")
        response = client.post(
            reverse("share-grant-list-create", args=[self.org.id]),
            {
                "resource_type": "inventory_operations",
                "resource_id": str(self.instance.id),
                "principal_type": "user",
                "user_id": str(user.id),
                "level": "sell",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._sell(client).status_code, 403)

    def test_share_levels_are_validated_per_resource_type(self):
        user, _ = self._member("levels@example.com")

        def share(resource_type, resource_id, level):
            return self.client.post(
                reverse("share-grant-list-create", args=[self.org.id]),
                {
                    "resource_type": resource_type,
                    "resource_id": str(resource_id),
                    "principal_type": "user",
                    "user_id": str(user.id),
                    "level": level,
                },
                format="json",
            ).status_code

        self.assertEqual(share("inventory_operations", self.instance.id, "read"), 400)
        self.assertEqual(share("app_model", self.models["part"].id, "sell"), 400)
        self.assertEqual(share("inventory_operations", "00000000-0000-0000-0000-000000000000", "sell"), 400)


class LedgerAndExistingRestrictionTests(OperationBase):
    def test_insufficient_stock_is_refused_despite_full_authority_and_leaves_no_trace(self):
        _, client = self._seller()
        before = self._counts()
        response = self._sell(client, quantity=51)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("would go negative", str(response.data))
        self.assertEqual(self._counts(), before)  # no ghost order, line, movement or invoice
        self.assertEqual(self._balance(), 50)

    def test_a_multi_line_sale_where_the_second_line_oversells_undoes_the_first(self):
        _, client = self._seller()
        other = self._create("part", name="Brake Pad Set")
        body = self._sale_body(quantity=2)
        body["lines"].append(
            {
                "part": str(other["id"]),
                "warehouse": str(self.warehouse["id"]),
                "quantity": 1,
                "unit_price": "40.00",
            }
        )
        before = self._counts()
        response = self._sell(client, **{"lines": body["lines"]})
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self._counts(), before)
        self.assertEqual(self._balance(), 50)

    def test_module_restrictions_still_apply_underneath_the_operation_authority(self):
        user, client = self._member("no-module@example.com")
        self._model_access(user, ("sales_order", "sales_order_line"))  # no write on the invoice model
        self._authority(user, "sell")
        before = self._counts()
        response = self._sell(client)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(self._counts(), before)  # the order and lines it had already made were rolled back
        self.assertEqual(self._balance(), 50)

    def test_a_receive_with_a_supplier_needs_the_purchase_order_models_but_one_without_does_not(self):
        user, client = self._member("bare-receiver@example.com")
        self._authority(user, "receive")
        no_supplier = self._receive_op(client, quantity=2, key="b1")
        self.assertEqual(no_supplier.status_code, 201, no_supplier.data)
        with_supplier = self._receive_op(
            client, quantity=2, key="b2", supplier=str(self.supplier["id"]), unit_cost="9.50"
        )
        self.assertEqual(with_supplier.status_code, 403, with_supplier.data)
        self.assertEqual(self._balance(), 52)
        self.assertEqual(self._records("purchase_order"), [])

    def test_a_receive_with_a_supplier_records_a_received_purchase_order_and_line(self):
        _, client = self._receiver()
        response = self._receive_op(
            client, quantity=10, supplier=str(self.supplier["id"]), unit_cost="9.50", reference="DN-77"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(self._records("purchase_order")), 1)
        self.assertEqual(len(self._records("purchase_order_line")), 1)
        self.assertEqual(self._balance(), 60)

    def test_a_sale_records_order_lines_movements_and_invoice_together(self):
        _, client = self._seller()
        response = self._sell(client, quantity=5, invoice="INV-20260920-AB1CD")
        self.assertEqual(response.status_code, 201, response.data)
        refs = {r["ref"] for r in response.data["results"] if r["ref"]}
        self.assertEqual(refs, {"order"})
        counts = self._counts()
        self.assertEqual((counts["sales_order"], counts["sales_order_line"], counts["invoice"]), (1, 1, 1))
        self.assertEqual(counts["stock_movement"], 2)
        sale = [
            m
            for m in self._records("stock_movement")
            if m[self._definition_id("stock_movement", "movement_type")] == "sale"
        ][0]
        self.assertEqual(sale[self._definition_id("stock_movement", "quantity_delta")], -5)
        self.assertEqual(sale[self._definition_id("stock_movement", "reference")], "INV-20260920-AB1CD")
        self.assertEqual(self._balance(), 45)


class ContractTests(OperationBase):
    def test_a_replayed_request_deducts_stock_once(self):
        _, client = self._seller()
        body = self._sale_body(quantity=4, invoice="INV-DUP-1")
        first = self._operation(client, "sell", body, "same-key")
        again = self._operation(client, "sell", body, "same-key")
        self.assertEqual((first.status_code, again.status_code), (201, 201))
        self.assertEqual(self._balance(), 46)
        self.assertEqual(self._counts()["invoice"], 1)

    def test_the_same_key_with_different_content_is_a_conflict_not_a_second_sale(self):
        _, client = self._seller()
        self.assertEqual(self._operation(client, "sell", self._sale_body(1, "INV-C-1"), "k").status_code, 201)
        changed = self._operation(client, "sell", self._sale_body(2, "INV-C-1"), "k")
        self.assertIn(changed.status_code, (400, 409), changed.data)
        self.assertEqual(self._balance(), 49)

    def test_an_idempotency_key_is_required(self):
        _, client = self._seller()
        before = self._counts()
        response = self._operation(client, "sell", self._sale_body(), key=None)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self._counts(), before)

    def test_input_is_validated_and_a_rejection_commits_nothing(self):
        _, client = self._seller()
        before = self._counts()
        bad = [
            {"quantity": 0},
            {"lines": []},
            {"occurred_at": "2026-09-19T13:35:00.646Z"},
            {"occurred_at": stamp(datetime.timedelta(days=2))},
            {"occurred_at": stamp(-datetime.timedelta(days=90))},
            {"invoice_number": "bad number!"},
            {"unknown": "field"},
            {"customer": "not-a-uuid"},
        ]
        for i, change in enumerate(bad):
            if "quantity" in change:
                body = self._sale_body()
                body["lines"][0]["quantity"] = 0
            else:
                body = self._sale_body(**change)
            response = self._operation(client, "sell", body, f"bad-{i}")
            self.assertEqual(response.status_code, 400, (change, response.data))
        self.assertEqual(self._counts(), before)
        self.assertEqual(self._balance(), 50)

    def test_the_operation_endpoints_are_not_open_to_bearer_token_clients(self):
        from app_platform.record_views import ReceiveView, SellView

        self.assertEqual(SellView.service_account_methods, frozenset())
        self.assertEqual(ReceiveView.service_account_methods, frozenset())
