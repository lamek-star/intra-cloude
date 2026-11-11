"""Ads API (ADR-0022 phase 4): the owner's side (movies.manage, a signed-in session) and the portal's side
(the shop's open portal; no sign-in needed to see the shop's ads)."""

from django.http import Http404, HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from . import ads
from .models import Ad
from .portal_views import PortalView, _is_uuid
from .views import OwnerView, _can, _forbidden, get_member_organization, get_member_shop


def ad_json(ad: Ad, *, owner: bool) -> dict:
    out = {
        "id": str(ad.id),
        "title": ad.title,
        "text": ad.text,
        "advertiser": ad.advertiser,
        "film": str(ad.film_id) if ad.film_id else None,
        "film_title": ad.film.title if ad.film_id else None,
        "link": ad.link,
        "has_picture": ad.picture_id is not None,
        # Changes when the picture does, so a browser never shows a replaced picture from its cache.
        "picture_version": str(ad.picture_id)[:8] if ad.picture_id else "",
    }
    if owner:
        out.update(
            {
                "starts_on": ad.starts_on.isoformat() if ad.starts_on else None,
                "ends_on": ad.ends_on.isoformat() if ad.ends_on else None,
                "active": ad.active,
                "position": ad.position,
                "views": ad.views,
                "taps": ad.taps,
                "showing": ads.showing(ad.shop).filter(id=ad.id).exists(),
                "created_at": ad.created_at.isoformat(),
            }
        )
    return out


def _picture_response(ad: Ad) -> HttpResponse:
    picture = ads.read_picture(ad)
    if picture is None:
        raise Http404
    data, mime = picture
    response = HttpResponse(data, content_type=mime)
    response["Cache-Control"] = "private, max-age=600"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _member_ad(user, ad_id) -> Ad:
    ad = (
        Ad.objects.select_related("shop", "film", "picture").filter(id=ad_id).first()
        if _is_uuid(ad_id)
        else None
    )
    if ad is None:
        raise Http404
    get_member_organization(user, ad.shop.organization_id)
    return ad


class AdListCreateView(OwnerView):
    def get(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.manage", shop):
            return _forbidden()
        return Response([ad_json(a, owner=True) for a in shop.ads.select_related("film", "shop")])

    def post(self, request, shop_id):
        shop = get_member_shop(request.user, shop_id)
        if not _can(request.user, "movies.manage", shop):
            return _forbidden()
        ad = ads.create_ad(
            shop, actor=request.user, data=request.data if isinstance(request.data, dict) else {}
        )
        return Response(ad_json(ad, owner=True), status=status.HTTP_201_CREATED)


class AdDetailView(OwnerView):
    def patch(self, request, ad_id):
        ad = _member_ad(request.user, ad_id)
        if not _can(request.user, "movies.manage", ad.shop):
            return _forbidden()
        ads.update_ad(ad, actor=request.user, data=request.data if isinstance(request.data, dict) else {})
        return Response(ad_json(ad, owner=True))

    def delete(self, request, ad_id):
        ad = _member_ad(request.user, ad_id)
        if not _can(request.user, "movies.manage", ad.shop):
            return _forbidden()
        ads.delete_ad(ad, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdPictureView(OwnerView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, ad_id):
        ad = _member_ad(request.user, ad_id)
        if not _can(request.user, "movies.manage", ad.shop):
            return _forbidden()
        return _picture_response(ad)

    def post(self, request, ad_id):
        ad = _member_ad(request.user, ad_id)
        if not _can(request.user, "movies.manage", ad.shop):
            return _forbidden()
        ads.set_picture(ad, actor=request.user, upload=request.FILES.get("file"))
        return Response(ad_json(ad, owner=True))


# ---- the portal ------------------------------------------------------------------------------------------
class PortalAdsView(PortalView):
    def get(self, request, shop_id):
        shop = self.shop(shop_id)
        showing = list(ads.showing(shop)[:10])
        ads.count_views(showing)
        return Response([ad_json(a, owner=False) for a in showing])


def _showing_ad(shop, ad_id) -> Ad:
    ad = ads.showing(shop).select_related("picture").filter(id=ad_id).first() if _is_uuid(ad_id) else None
    if ad is None:
        raise Http404
    return ad


class PortalAdPictureView(PortalView):
    def get(self, request, shop_id, ad_id):
        return _picture_response(_showing_ad(self.shop(shop_id), ad_id))


class PortalAdTapView(PortalView):
    def post(self, request, shop_id, ad_id):
        ad = _showing_ad(self.shop(shop_id), ad_id)
        ads.count_tap(ad)
        return Response({"film": str(ad.film_id) if ad.film_id else None, "link": ad.link})
