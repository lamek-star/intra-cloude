from django.urls import path

from . import app_pay, internal_views, views

urlpatterns = [
    path("service-apps/", views.ServiceAppListView.as_view()),
    path("service-apps/<uuid:app_id>/", views.ServiceAppDetailView.as_view()),
    path("service-apps/<uuid:app_id>/launch/", views.ServiceAppLaunchView.as_view()),
    path("service-apps/<uuid:app_id>/sign-in/", views.ServiceAppSignInInfoView.as_view()),
    path("service-apps/<uuid:app_id>/removal-preview/", views.ServiceAppRemovalPreviewView.as_view()),
    path("service-apps/<uuid:app_id>/reinstate/", views.ServiceAppReinstateView.as_view()),
    # IntraForge Pay for Application credentials (ADR-0020), e.g. a hosted Node.js app.
    path("pay/payment-requests/", app_pay.AppPayRequestsView.as_view(), name="app-pay-requests"),
    path(
        "pay/payment-requests/<uuid:request_id>/",
        app_pay.AppPayRequestDetailView.as_view(),
        name="app-pay-request-detail",
    ),
    # Internal (service token, internal network only; the proxy refuses /api/v1/internal/).
    path("internal/service-apps/self/", internal_views.InternalSelfView.as_view()),
    path("internal/service-apps/heartbeat/", internal_views.InternalHeartbeatView.as_view()),
    path("internal/service-apps/sessions/introspect/", internal_views.InternalIntrospectView.as_view()),
    path("internal/service-apps/sessions/revoke/", internal_views.InternalRevokeView.as_view()),
    path("internal/service-apps/users/", internal_views.InternalUsersView.as_view()),
    path("internal/service-apps/audit-events/", internal_views.InternalAuditView.as_view()),
    path("internal/service-apps/config/", internal_views.InternalConfigView.as_view()),
    path("internal/service-apps/files/", internal_views.InternalFilesView.as_view()),
    path("internal/service-apps/pay/payment-requests/", internal_views.InternalPayRequestsView.as_view()),
    path(
        "internal/service-apps/pay/payment-requests/<uuid:request_id>/",
        internal_views.InternalPayRequestDetailView.as_view(),
    ),
    path("internal/service-apps/files/<uuid:file_id>/", internal_views.InternalFileDetailView.as_view()),
]
