"""The customer portal's API (ADR-0022 phase 3), at /api/v1/portal/<shop>/.

No IntraForge authentication runs here: the only identity is the portal cookie (portal.py). Every request
names the shop, and a customer is found only among that shop's own customers, so one shop's customer can never
reach another shop. A request that changes something must carry the X-Portal-Request header, which a page on
another site cannot send without a CORS preflight IntraForge never grants; the cookie is SameSite=Strict as
well. The portal is served only on the shop network: the internet gate (port 8446) serves published sites and
nothing else.
"""

from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponse
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView

from . import portal, services
from .models import MovieShop, PortalCustomer, Sale, Title

HEADER = "HTTP_X_PORTAL_REQUEST"


def _is_uuid(value) -> bool:
    import uuid

    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def customer_json(customer: PortalCustomer, *, with_wallet: bool = False) -> dict:
    out = {
        "id": str(customer.id),
        "name": customer.name,
        "phone": customer.phone,
        "status": customer.status,
        "points": portal.points_of(customer),
        "referral_code": customer.referral_code
        if customer.status == PortalCustomer.Status.APPROVED
        else None,
        "birthday": customer.birthday.isoformat() if customer.birthday else None,
        "created_at": customer.created_at.isoformat(),
    }
    if with_wallet:
        out["wallet"] = portal.wallet_of(customer)
    return out


def _rules(shop: MovieShop) -> dict:
    return {
        "welcome_points": shop.welcome_points,
        "referral_points": shop.referral_points,
        "birthday_points": shop.birthday_points,
        "every_nth_free": shop.every_nth_free,
    }


def portal_title_json(t: Title, prices: dict, default: int) -> dict:
    """What a customer sees of a title: never where it is on the shop's disks."""
    return {
        "id": str(t.id),
        "category": t.category,
        "title": t.title,
        "year": t.year,
        "kind": t.kind,
        "size_bytes": t.size_bytes,
        "episodes": t.episodes,
        "has_cover": t.cover_id is not None,
        "price": services.price_of(t, prices, default),
        "description": t.description,
    }


def order_json(sale: Sale) -> dict:
    return {
        "id": str(sale.id),
        "number": sale.number,
        "status": sale.status,
        "total": sale.total,
        "discount": sale.discount,
        "points_used": sale.points_used,
        "use_points": sale.use_points,
        "created_at": sale.created_at.isoformat(),
        "lines": [
            {"title": line.title_name, "category": line.category, "price": line.price, "free": line.free}
            for line in sale.lines.all()
        ],
    }


class PortalView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.META.get(HEADER) != "1":
            raise PermissionDenied("Reload the page and try again.")

    def get_authenticate_header(self, request):
        # "Not signed in" is a 401 with its own challenge (DRF answers 403 when a view has no authenticator).
        return 'Portal realm="shop portal"'

    def shop(self, shop_id) -> MovieShop:
        shop = MovieShop.objects.filter(id=shop_id, portal_open=True).first() if _is_uuid(shop_id) else None
        if shop is None:
            raise Http404
        return shop

    def customer(self, request, shop) -> PortalCustomer | None:
        return portal.customer_for_token(shop, request.COOKIES.get(portal.COOKIE))

    def signed_in(self, request, shop) -> PortalCustomer:
        customer = self.customer(request, shop)
        if customer is None:
            raise NotAuthenticated("Sign in to the shop's portal.")
        return customer

    def with_cookie(self, response: Response, token: str) -> Response:
        response.set_cookie(
            portal.COOKIE,
            token,
            max_age=portal.SESSION_DAYS * 86400,
            path=portal.COOKIE_PATH,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=True,
            samesite="Strict",
        )
        return response


class PortalHomeView(PortalView):
    def get(self, request, shop_id):
        shop = self.shop(shop_id)
        customer = self.customer(request, shop)
        return Response(
            {
                "shop": {"id": str(shop.id), "name": shop.name, "rules": _rules(shop)},
                "customer": customer_json(customer) if customer else None,
            }
        )


class PortalSignUpView(PortalView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, shop_id):
        shop = self.shop(shop_id)
        customer, token = portal.sign_up(shop, request.data if isinstance(request.data, dict) else {})
        return self.with_cookie(Response(customer_json(customer), status=status.HTTP_201_CREATED), token)


class PortalSignInView(PortalView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, shop_id):
        shop = self.shop(shop_id)
        data = request.data if isinstance(request.data, dict) else {}
        customer, token = portal.sign_in(shop, data.get("phone"), data.get("password"))
        return self.with_cookie(Response(customer_json(customer)), token)


class PortalSignOutView(PortalView):
    def post(self, request, shop_id):
        self.shop(shop_id)
        portal.sign_out(request.COOKIES.get(portal.COOKIE))
        response = Response({"ok": True})
        response.delete_cookie(portal.COOKIE, path=portal.COOKIE_PATH, samesite="Strict")
        return response


class PortalMeView(PortalView):
    def get(self, request, shop_id):
        shop = self.shop(shop_id)
        customer = self.signed_in(request, shop)
        portal.give_birthday_points(customer)
        out = customer_json(customer, with_wallet=True)
        out["points_history"] = [
            {"delta": e.delta, "reason": e.reason, "note": e.note, "at": e.created_at.isoformat()}
            for e in customer.points.all()[:50]
        ]
        return Response(out)


class PortalCategoriesView(PortalView):
    def get(self, request, shop_id):
        shop = self.shop(shop_id)
        self.signed_in(request, shop)
        return Response([{"name": c["name"], "count": c["count"]} for c in services.category_summary(shop)])


class PortalTitlesView(PortalView):
    def get(self, request, shop_id):
        shop = self.shop(shop_id)
        self.signed_in(request, shop)
        qs = shop.titles.filter(hidden=False)
        params = request.query_params
        if params.get("category"):
            qs = qs.filter(category__iexact=params["category"][:120])
        if params.get("q"):
            q = params["q"][:100]
            qs = qs.filter(Q(title__icontains=q) | Q(category__icontains=q))
        if params.get("sort") == "newest":
            qs = qs.order_by("-created_at")
        prices = {p.category.lower(): p.price for p in shop.category_prices.all()}
        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            [portal_title_json(t, prices, shop.default_price) for t in page]
        )


class PortalTitleView(PortalView):
    def get(self, request, shop_id, title_id):
        shop = self.shop(shop_id)
        self.signed_in(request, shop)
        title = shop.titles.filter(id=title_id, hidden=False).first() if _is_uuid(title_id) else None
        if title is None:
            raise Http404
        prices = {p.category.lower(): p.price for p in shop.category_prices.all()}
        return Response(portal_title_json(title, prices, shop.default_price))


class PortalCoverView(PortalView):
    def get(self, request, shop_id, title_id):
        shop = self.shop(shop_id)
        self.signed_in(request, shop)
        title = (
            shop.titles.select_related("cover").filter(id=title_id, hidden=False).first()
            if _is_uuid(title_id)
            else None
        )
        cover = services.read_cover(title) if title else None
        if cover is None:
            raise Http404
        data, mime = cover
        response = HttpResponse(data, content_type=mime)
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class PortalOrdersView(PortalView):
    def get(self, request, shop_id):
        shop = self.shop(shop_id)
        customer = self.signed_in(request, shop)
        orders = customer.sales.prefetch_related("lines").order_by("-created_at")[:30]
        return Response([order_json(s) for s in orders])

    def post(self, request, shop_id):
        from . import sales

        shop = self.shop(shop_id)
        customer = self.signed_in(request, shop)
        data = request.data if isinstance(request.data, dict) else {}
        use_points = data.get("use_points") is True
        if data.get("preview") is True:
            lines = sales.build_lines(shop, data.get("titles"))
            priced = portal.price_with_rewards(shop, customer, lines, use_points)
            return Response(
                {
                    "subtotal": sum(line.price for line in lines),
                    "discount": priced["discount"],
                    "points_used": priced["points_used"],
                    "total": priced["total"],
                    "free_titles": [lines[i].title_name for i in sorted(priced["free"])],
                }
            )
        sale = portal.place_order(customer, data.get("titles"), use_points)
        return Response(order_json(sale), status=status.HTTP_201_CREATED)


class PortalOrderCancelView(PortalView):
    def post(self, request, shop_id, sale_id):
        shop = self.shop(shop_id)
        customer = self.signed_in(request, shop)
        sale = customer.sales.filter(id=sale_id).first() if _is_uuid(sale_id) else None
        if sale is None:
            raise Http404
        return Response(order_json(portal.cancel_order(customer, sale)))
