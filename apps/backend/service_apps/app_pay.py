"""
IntraForge Pay for applications (ADR-0020 decision 2): an Application credential -- for example a hosted
Node.js app's IF_API_TOKEN -- asks this organization's IntraForge Pay to take a payment, through the same
Pay bridge the service applications use (pay_bridge.py). IntraForge picks the Pay (the application's own
organization), and the payment is taken by the application's service account, which therefore needs
``ifpay.checkout`` granted on that Pay (Applications > the application > IntraForge Pay). Browser sessions
cannot use these endpoints: a person takes payments in Pay itself or from Spare Parts.

    POST /api/v1/pay/payment-requests/   {"amountMinor": 2500, "reference": "Order 42", "externalId": "42"}
    GET  /api/v1/pay/payment-requests/<id>/
"""

from __future__ import annotations

from dataclasses import dataclass

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.models import ApplicationCredential
from audit import services as audit

from . import pay_bridge
from .sessions import capabilities_for

APPLICATION_CALLER = "application"


@dataclass(frozen=True)
class ApplicationCaller:
    """What the Pay bridge needs to know about who is asking."""

    id: object
    organization_id: object
    app_type: str
    product_name: str


def _caller(request) -> tuple[ApplicationCaller, object]:
    credential = request.auth
    if not isinstance(credential, ApplicationCredential):
        raise PermissionDenied("Only an application's own credential can ask IntraForge Pay for a payment.")
    application = credential.service_account.application
    caller = ApplicationCaller(
        id=application.id,
        organization_id=application.organization_id,
        app_type=APPLICATION_CALLER,
        product_name=application.name[:120],
    )
    return caller, credential.service_account.identity_user


class AppPayRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        caller, identity = _caller(request)
        pay, _ = pay_bridge.pay_for(caller)
        if "ifpay.checkout" not in capabilities_for(identity, pay):
            raise PermissionDenied(
                "This application may not take IntraForge Pay payments yet. In IntraForge, open "
                "Applications, this application, and allow IntraForge Pay."
            )
        data = request.data if isinstance(request.data, dict) else {}
        result = pay_bridge.create_request(
            caller,
            actor_id=identity.pk,
            amount_minor=data.get("amountMinor"),
            reference=data.get("reference"),
            external_id=data.get("externalId"),
        )
        user = result.pop("user")
        audit.record(
            actor=user,
            organization_id=caller.organization_id,
            action="application.pay_request",
            resource_type="service_app",
            resource_id=result["pay"]["id"],
            context={
                "requested_by": {
                    "id": str(caller.id),
                    "type": APPLICATION_CALLER,
                    "name": caller.product_name,
                },
                "pay_request_id": result["id"],
                "amount_minor": result["amount_minor"],
                "reference": result["reference"],
            },
        )
        return Response(result, status=status.HTTP_201_CREATED)


class AppPayRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        caller, _ = _caller(request)
        return Response(pay_bridge.request_status(caller, request_id))
