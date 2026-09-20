"""Record CRUD over a provisioned app runtime; see records.py for the
translation/authorization/validation this thin view layer delegates to."""

import uuid

from django.http import Http404
from rest_framework.response import Response

from databases import rows as row_ops

from . import inventory_authority, inventory_operations, records, transactions
from .access import environment_scope_denied, get_owned
from .models import AppInstance, ModelDefinition
from .views import FoundationView

_RESERVED_QUERY_PARAMS = {"limit", "offset", "ordering", "search", "ids"}
# One request can name at most this many records by id. Screens use it to put names next to the ids in a
# page of rows (one request instead of one per row), so it only needs to cover a page.
MAX_IDS = 100


def _get_model(request, object_id):
    return get_owned(ModelDefinition, object_id, request.user, "instance__organization")


class RecordListCreateView(FoundationView):
    # The core of the external bearer-token surface (Post-Phase-3
    # Integration Enablement) -- gated below purely by the same
    # database.read/database.write ResourceGrant a human session needs
    # (records.py's resolve()), nothing looser.
    service_account_methods = frozenset({"GET", "POST"})

    def get(self, request, object_id):
        model = _get_model(request, object_id)
        if environment_scope_denied(request, model):
            return Response(status=403)
        try:
            limit = int(request.query_params.get("limit", row_ops.DEFAULT_LIMIT))
            offset = int(request.query_params.get("offset", 0))
        except ValueError:
            return Response({"detail": "limit/offset must be integers"}, status=400)
        filters = {k: v for k, v in request.query_params.items() if k not in _RESERVED_QUERY_PARAMS}
        raw_ids = request.query_params.get("ids")
        if raw_ids is not None:
            if "id" in filters:
                return Response({"detail": "use either id or ids, not both"}, status=400)
            try:
                ids = [str(uuid.UUID(part.strip())) for part in raw_ids.split(",") if part.strip()]
            except ValueError:
                return Response({"detail": "ids must be a comma-separated list of record ids"}, status=400)
            if len(ids) > MAX_IDS:
                return Response({"detail": f"at most {MAX_IDS} ids per request"}, status=400)
            filters["id"] = ids  # an IN-list through the same, permission-checked list path
        try:
            result = records.list_records(
                request.user,
                model,
                limit=limit,
                offset=offset,
                ordering=request.query_params.get("ordering"),
                filters=filters,
                search=request.query_params.get("search"),
            )
        except records.RecordAccessDenied:
            return Response(status=403)
        except records.RecordValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(result)

    def post(self, request, object_id):
        model = _get_model(request, object_id)
        if environment_scope_denied(request, model):
            return Response(status=403)
        try:
            row = records.create_record(
                request.user,
                model,
                request.data,
                idempotency_key=request.headers.get("Idempotency-Key"),
            )
        except records.RecordAccessDenied:
            return Response(status=403)
        except records.RecordValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(row, status=201)


class RecordDetailView(FoundationView):
    service_account_methods = frozenset({"GET", "PATCH", "DELETE"})

    def get(self, request, object_id, record_id):
        model = _get_model(request, object_id)
        if environment_scope_denied(request, model):
            return Response(status=403)
        try:
            row = records.get_record(request.user, model, record_id)
        except records.RecordAccessDenied:
            return Response(status=403)
        except row_ops.RowNotFound as exc:
            raise Http404 from exc
        return Response(row)

    def patch(self, request, object_id, record_id):
        model = _get_model(request, object_id)
        if environment_scope_denied(request, model):
            return Response(status=403)
        try:
            row = records.update_record(request.user, model, record_id, request.data)
        except records.RecordAccessDenied:
            return Response(status=403)
        except records.RecordValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except row_ops.RowNotFound as exc:
            raise Http404 from exc
        return Response(row)

    def delete(self, request, object_id, record_id):
        model = _get_model(request, object_id)
        if environment_scope_denied(request, model):
            return Response(status=403)
        try:
            records.delete_record(request.user, model, record_id)
        except records.RecordAccessDenied:
            return Response(status=403)
        except records.RecordValueError as exc:
            # Was already reachable pre-existing (e.g. another table's
            # RESTRICT foreign key blocking this delete) with no handler
            # here, unlike get/patch/post above -- a real 500 leak this
            # feature's own delete-guard trigger (quantity_ledger.py) made
            # newly certain to hit, not newly introduced by it.
            return Response({"detail": str(exc)}, status=400)
        except row_ops.RowNotFound as exc:
            raise Http404 from exc
        return Response(status=204)


class TransactionView(FoundationView):
    """Several record operations committed as one unit (transactions.py).
    Human session only: no `service_account_methods`, so an external bearer-
    token client keeps using ordinary single-record CRUD. Authorization is
    per operation, inside transactions.run -> records.*."""

    def post(self, request, object_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        try:
            results = transactions.run(
                request.user, instance, request.data, idempotency_key=request.headers.get("Idempotency-Key")
            )
        except transactions.TransactionDenied as exc:
            return Response({"detail": str(exc), "operation": exc.index}, status=403)
        except transactions.TransactionError as exc:
            return Response({"detail": str(exc), "operation": exc.index}, status=400)
        return Response({"results": results}, status=201)


class _InventoryOperationView(FoundationView):
    """A controlled business operation (ADR-0017): human session only (no `service_account_methods`), an
    Idempotency-Key is mandatory, and authority is the operation's own capability -- never a request field."""

    def run(self, request, instance):
        """Performs the operation and returns its results; implemented by the two subclasses."""
        raise NotImplementedError

    def post(self, request, object_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        try:
            results = self.run(request, instance)
        except inventory_authority.OperationDenied as exc:
            return Response({"detail": str(exc)}, status=403)
        except inventory_operations.OperationUnsupported as exc:
            return Response({"detail": str(exc)}, status=400)
        except transactions.TransactionDenied as exc:
            return Response({"detail": str(exc), "operation": exc.index}, status=403)
        except transactions.TransactionError as exc:
            return Response({"detail": str(exc), "operation": exc.index}, status=400)
        return Response({"results": results}, status=201)


class SellView(_InventoryOperationView):
    def run(self, request, instance):
        return inventory_operations.sell(
            request.user, instance, request.data, idempotency_key=request.headers.get("Idempotency-Key")
        )


class ReceiveView(_InventoryOperationView):
    def run(self, request, instance):
        return inventory_operations.receive(
            request.user, instance, request.data, idempotency_key=request.headers.get("Idempotency-Key")
        )
