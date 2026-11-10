"""Movie Shop API (ADR-0022). Owner endpoints take only a signed-in person's session (never an application
credential); the media agent's endpoints take only that shop's own agent credential."""

from django.db.models import Q
from django.http import Http404, HttpResponse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.authentication import ServiceAccountAuthentication
from organizations.services import get_member_organization
from permissions.services import has_permission
from workspaces.views import get_member_project

from . import services
from .models import Library, MovieShop, Title

RESOURCE = "movie_shop"


def _can(user, code: str, shop: MovieShop) -> bool:
    return has_permission(user, code, organization_id=shop.organization_id, resource=(RESOURCE, str(shop.id)))


def _forbidden():
    return Response(
        {"detail": "You don't have permission to do this in this movie shop."},
        status=status.HTTP_403_FORBIDDEN,
    )


def get_member_shop(user, shop_id) -> MovieShop:
    """A shop only if the requester belongs to its organization; otherwise 404 (THREAT_MODEL.md Section 4)."""
    shop = MovieShop.objects.filter(id=shop_id).first()
    if shop is None:
        raise Http404
    get_member_organization(user, shop.organization_id)
    return shop


def _shop_json(shop: MovieShop, *, can_manage: bool, can_sell: bool = False) -> dict:
    return {
        "id": str(shop.id),
        "organization": str(shop.organization_id),
        "project": str(shop.project_id),
        "name": shop.name,
        "default_price": shop.default_price,
        "category_prices": {p.category: p.price for p in shop.category_prices.all()},
        "agent_seen_at": shop.agent_seen_at.isoformat() if shop.agent_seen_at else None,
        "agent": {
            "computer": shop.agent_report.get("computer", ""),
            "version": shop.agent_report.get("agent_version", ""),
        },
        "titles": shop.titles.filter(hidden=False).count(),
        "can_manage": can_manage,
        "can_sell": can_sell,
        "created_at": shop.created_at.isoformat(),
    }


def _library_json(lib: Library) -> dict:
    return {
        "id": str(lib.id),
        "name": lib.name,
        "path": lib.path,
        "kind": lib.kind,
        "total_bytes": lib.total_bytes,
        "free_bytes": lib.free_bytes,
        "titles": lib.titles.count(),
        "scan_requested": lib.scan_requested_at is not None,
        "last_scan_at": lib.last_scan_at.isoformat() if lib.last_scan_at else None,
        "last_scan_message": lib.last_scan_message,
    }


def _title_json(t: Title, prices: dict, default: int) -> dict:
    return {
        "id": str(t.id),
        "library": str(t.library_id),
        "relative_path": t.relative_path,
        "category": t.category,
        "title": t.title,
        "year": t.year,
        "kind": t.kind,
        "size_bytes": t.size_bytes,
        "episodes": t.episodes,
        "has_cover": t.cover_id is not None,
        "price": services.price_of(t, prices, default),
        "own_price": t.price,
        "hidden": t.hidden,
        "description": t.description,
    }


class OwnerView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]


class ShopListCreateView(OwnerView):
    def get(self, request, organization_id):
        organization = get_member_organization(request.user, organization_id)
        shops = [
            s
            for s in MovieShop.objects.filter(organization=organization)
            if _can(request.user, "movies.read", s)
        ]
        return Response([_shop_json(s, can_manage=_can(request.user, "movies.manage", s)) for s in shops])

    def post(self, request, organization_id):
        organization = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "movies.manage", organization_id=organization.id):
            return _forbidden()
        project = get_member_project(request.user, request.data.get("project"))
        shop = services.create_shop(
            actor=request.user, organization=organization, project=project, name=request.data.get("name")
        )
        return Response(_shop_json(shop, can_manage=True), status=status.HTTP_201_CREATED)


class ShopDetailView(OwnerView):
    def get(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.read", shop):
            return _forbidden()
        return Response(
            _shop_json(
                shop,
                can_manage=_can(request.user, "movies.manage", shop),
                can_sell=_can(request.user, "movies.sell", shop),
            )
        )


class DestinationsView(OwnerView):
    """The drives a sold title can be copied to (what the media agent sees now), for the person at the
    counter."""

    def get(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.sell", shop):
            return _forbidden()
        library_roots = {lib.path[:3].lower() for lib in shop.libraries.all()}
        drives = [
            {k: d.get(k) for k in ("root", "label", "kind", "total_bytes", "free_bytes")}
            for d in (shop.agent_report or {}).get("drives", [])
            if d.get("kind") == "removable" or d.get("root", "").lower() not in library_roots
        ]
        drives.sort(key=lambda d: d["kind"] != "removable")
        seen = shop.agent_seen_at.isoformat() if shop.agent_seen_at else None
        return Response({"agent_seen_at": seen, "drives": drives})


class ShopPricesView(OwnerView):
    def put(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.manage", shop):
            return _forbidden()
        services.set_prices(
            shop=shop,
            actor=request.user,
            default_price=request.data.get("default_price"),
            categories=request.data.get("categories", {}),
        )
        return Response(_shop_json(shop, can_manage=True))


class AgentCredentialView(OwnerView):
    def post(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.manage", shop):
            return _forbidden()
        token = services.issue_agent_credential(shop=shop, actor=request.user)
        return Response({"token": token}, status=status.HTTP_201_CREATED)


class DrivesView(OwnerView):
    def get(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.manage", shop):
            return _forbidden()
        return Response(
            {
                "agent_seen_at": shop.agent_seen_at.isoformat() if shop.agent_seen_at else None,
                **(shop.agent_report or {"drives": []}),
            }
        )


class LibraryListCreateView(OwnerView):
    def get(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.read", shop):
            return _forbidden()
        return Response([_library_json(lib) for lib in shop.libraries.all()])

    def post(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.manage", shop):
            return _forbidden()
        library = services.add_library(
            shop=shop,
            actor=request.user,
            path=request.data.get("path"),
            name=request.data.get("name", ""),
            kind=request.data.get("kind", "fixed"),
        )
        return Response(_library_json(library), status=status.HTTP_201_CREATED)


def _member_library(user, library_id) -> Library:
    library = Library.objects.select_related("shop").filter(id=library_id).first()
    if library is None:
        raise Http404
    get_member_organization(user, library.shop.organization_id)
    return library


class LibraryDetailView(OwnerView):
    def delete(self, request, library_id):
        library = _member_library(request.user, library_id)
        if not _can(request.user, "movies.manage", library.shop):
            return _forbidden()
        services.remove_library(library=library, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LibraryScanView(OwnerView):
    def post(self, request, library_id):
        library = _member_library(request.user, library_id)
        if not _can(request.user, "movies.manage", library.shop):
            return _forbidden()
        services.request_scan(library=library, actor=request.user)
        return Response(_library_json(library))


class CategoryListView(OwnerView):
    def get(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.read", shop):
            return _forbidden()
        library = (
            shop.libraries.filter(id=request.query_params.get("library")).first()
            if request.query_params.get("library")
            else None
        )
        return Response(services.category_summary(shop, library))


class TitleListView(OwnerView):
    def get(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.read", shop):
            return _forbidden()
        qs = shop.titles.all()
        params = request.query_params
        if params.get("library"):
            qs = qs.filter(library_id=params["library"]) if _is_uuid(params["library"]) else qs.none()
        if params.get("category"):
            qs = qs.filter(category__iexact=params["category"])
        if params.get("q"):
            q = params["q"][:100]
            qs = qs.filter(Q(title__icontains=q) | Q(relative_path__icontains=q))
        if params.get("hidden") != "1":
            qs = qs.filter(hidden=False)
        if params.get("sort") == "title":
            qs = qs.order_by("title")
        elif params.get("sort") == "newest":
            qs = qs.order_by("-created_at")
        prices = {p.category.lower(): p.price for p in shop.category_prices.all()}
        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response([_title_json(t, prices, shop.default_price) for t in page])


def _is_uuid(value) -> bool:
    import uuid

    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def _member_title(user, title_id) -> Title:
    title = (
        Title.objects.select_related("shop", "cover").filter(id=title_id).first()
        if _is_uuid(title_id)
        else None
    )
    if title is None:
        raise Http404
    get_member_organization(user, title.shop.organization_id)
    return title


class TitleDetailView(OwnerView):
    def patch(self, request, title_id):
        title = _member_title(request.user, title_id)
        if not _can(request.user, "movies.manage", title.shop):
            return _forbidden()
        services.edit_title(
            title=title, actor=request.user, data=request.data if isinstance(request.data, dict) else {}
        )
        prices = {p.category.lower(): p.price for p in title.shop.category_prices.all()}
        return Response(_title_json(title, prices, title.shop.default_price))


class TitleCoverView(OwnerView):
    def get(self, request, title_id):
        title = _member_title(request.user, title_id)
        if not _can(request.user, "movies.read", title.shop):
            return _forbidden()
        cover = services.read_cover(title)
        if cover is None:
            raise Http404
        data, mime = cover
        response = HttpResponse(data, content_type=mime)
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response


# ---- the media agent ---------------------------------------------------------------------------------------
class AgentView(APIView):
    """Only the shop's own media-agent credential (ADR-0022 decision 3)."""

    authentication_classes = [ServiceAccountAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def shop(self, request) -> MovieShop:
        shop = services.shop_for_agent(request.auth)
        if shop is None:
            raise Http404
        return shop

    def library(self, request, library_id) -> Library:
        shop = self.shop(request)
        library = shop.libraries.filter(id=library_id).first() if _is_uuid(library_id) else None
        if library is None:
            raise Http404
        return library


class AgentReportView(AgentView):
    def post(self, request):
        return Response(services.record_agent_report(shop=self.shop(request), data=request.data))


class AgentScanStartView(AgentView):
    def post(self, request, library_id):
        return Response({"generation": services.start_scan(library=self.library(request, library_id))})


class AgentScanTitlesView(AgentView):
    def post(self, request, library_id):
        library = self.library(request, library_id)
        return Response(
            services.add_scanned_titles(
                library=library, generation=request.data.get("generation"), items=request.data.get("titles")
            )
        )


class AgentScanFinishView(AgentView):
    def post(self, request, library_id):
        library = self.library(request, library_id)
        return Response(
            services.finish_scan(
                library=library,
                generation=request.data.get("generation"),
                message=request.data.get("message", ""),
            )
        )


class AgentCoverView(AgentView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, library_id):
        library = self.library(request, library_id)
        title = services.attach_cover(
            library=library,
            relative_path=request.data.get("relative_path"),
            fingerprint=request.data.get("fingerprint", ""),
            upload=request.FILES.get("file"),
        )
        return Response({"id": str(title.id)}, status=status.HTTP_201_CREATED)


# ---- counter sales (phase 2) ---------------------------------------------------------------------------
def _sale_json(sale) -> dict:
    lines = list(sale.lines.all())
    return {
        "id": str(sale.id),
        "number": sale.number,
        "status": sale.status,
        "method": sale.method,
        "customer_name": sale.customer_name,
        "total": sale.total,
        "destination": sale.destination,
        "folder": sale.folder,
        "pay": (
            {
                "code": sale.pay_code,
                "qr_svg": sale.pay_qr_svg,
                "expires_at": sale.pay_expires_at.isoformat() if sale.pay_expires_at else None,
            }
            if sale.status == "awaiting_payment" and sale.method == "ifpay"
            else None
        ),
        "receipt_number": sale.receipt_number,
        "paid_at": sale.paid_at.isoformat() if sale.paid_at else None,
        "created_at": sale.created_at.isoformat(),
        "lines": [
            {
                "id": str(line.id),
                "title": line.title_name,
                "title_id": str(line.title_id) if line.title_id else None,
                "category": line.category,
                "kind": line.kind,
                "price": line.price,
                "size_bytes": line.size_bytes,
                "copy_status": line.copy_status,
                "copied_bytes": line.copied_bytes,
                "copy_message": line.copy_message,
            }
            for line in lines
        ],
    }


def _can_sell(user, shop) -> bool:
    return _can(user, "movies.sell", shop)


def _member_sale(user, sale_id):
    from .models import Sale

    sale = Sale.objects.select_related("shop").filter(id=sale_id).first() if _is_uuid(sale_id) else None
    if sale is None:
        raise Http404
    get_member_organization(user, sale.shop.organization_id)
    return sale


class SaleListCreateView(OwnerView):
    def get(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not (_can_sell(request.user, shop) or _can(request.user, "movies.manage", shop)):
            return _forbidden()
        qs = shop.sales.all()
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(qs.prefetch_related("lines"), request, view=self)
        return paginator.get_paginated_response([_sale_json(s) for s in page])

    def post(self, request, shop_id):
        from . import sales

        shop = get_member_shop(request.user, shop_id)
        if not _can_sell(request.user, shop):
            return _forbidden()
        data = request.data if isinstance(request.data, dict) else {}
        sale = sales.create_sale(
            shop=shop,
            actor=request.user,
            title_ids=data.get("titles"),
            destination=data.get("destination"),
            method=data.get("method", "ifpay"),
            customer_name=data.get("customer_name", ""),
        )
        return Response(_sale_json(sale), status=status.HTTP_201_CREATED)


class SaleDetailView(OwnerView):
    def get(self, request, sale_id):
        from . import sales

        sale = _member_sale(request.user, sale_id)
        if not (_can_sell(request.user, sale.shop) or _can(request.user, "movies.manage", sale.shop)):
            return _forbidden()
        if _can_sell(request.user, sale.shop):
            sale = sales.refresh_payment(sale, actor=request.user)
        return Response(_sale_json(sale))


class SaleActionView(OwnerView):
    action_name = ""

    def post(self, request, sale_id):
        from . import sales

        sale = _member_sale(request.user, sale_id)
        if not _can_sell(request.user, sale.shop):
            return _forbidden()
        act = {"cash": sales.mark_cash, "cancel": sales.cancel, "retry": sales.retry_failed}[self.action_name]
        return Response(_sale_json(act(sale, actor=request.user)))


class AgentCopyProgressView(AgentView):
    def post(self, request, line_id):
        from . import sales

        line = sales.copy_progress(shop=self.shop(request), line_id=line_id, data=request.data)
        return Response({"status": line.copy_status, "sale_status": line.sale.status})
