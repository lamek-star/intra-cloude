"""Record CRUD over a provisioned app runtime; see records.py for the
translation/authorization/validation this thin view layer delegates to."""

from django.http import Http404
from rest_framework.response import Response

from databases import rows as row_ops

from . import records
from .access import get_owned
from .models import ModelDefinition
from .views import FoundationView

_RESERVED_QUERY_PARAMS = {"limit", "offset", "ordering", "search"}


def _get_model(request, object_id):
    return get_owned(ModelDefinition, object_id, request.user, "instance__organization")


class RecordListCreateView(FoundationView):
    def get(self, request, object_id):
        model = _get_model(request, object_id)
        try:
            limit = int(request.query_params.get("limit", row_ops.DEFAULT_LIMIT))
            offset = int(request.query_params.get("offset", 0))
        except ValueError:
            return Response({"detail": "limit/offset must be integers"}, status=400)
        filters = {k: v for k, v in request.query_params.items() if k not in _RESERVED_QUERY_PARAMS}
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
        try:
            row = records.create_record(request.user, model, request.data)
        except records.RecordAccessDenied:
            return Response(status=403)
        except records.RecordValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(row, status=201)


class RecordDetailView(FoundationView):
    def get(self, request, object_id, record_id):
        model = _get_model(request, object_id)
        try:
            row = records.get_record(request.user, model, record_id)
        except records.RecordAccessDenied:
            return Response(status=403)
        except row_ops.RowNotFound as exc:
            raise Http404 from exc
        return Response(row)

    def patch(self, request, object_id, record_id):
        model = _get_model(request, object_id)
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
        try:
            records.delete_record(request.user, model, record_id)
        except records.RecordAccessDenied:
            return Response(status=403)
        except row_ops.RowNotFound as exc:
            raise Http404 from exc
        return Response(status=204)
