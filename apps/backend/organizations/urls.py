from django.urls import path

from . import access_views, views

urlpatterns = [
    # Access requests (ADR-0026).
    path("access/apps/<uuid:app_id>/", access_views.AppAccessView.as_view(), name="app-access"),
    path(
        "organizations/<uuid:organization_id>/access-requests/",
        access_views.OrganizationAccessRequestsView.as_view(),
        name="organization-access-requests",
    ),
    path(
        "organizations/<uuid:organization_id>/access-requests/<uuid:request_id>/<str:decision>/",
        access_views.OrganizationAccessRequestDecisionView.as_view(),
        name="organization-access-request-decision",
    ),
    path(
        "organizations/<uuid:organization_id>/members/<uuid:membership_id>/reset-password/",
        views.MembershipPasswordResetView.as_view(),
        name="membership-password-reset",
    ),
    path(
        "organizations/<uuid:organization_id>/members/<uuid:membership_id>/profile/",
        views.MembershipProfileView.as_view(),
        name="membership-profile",
    ),
    path("organizations/", views.OrganizationListCreateView.as_view(), name="organization-list-create"),
    path(
        "organizations/<uuid:organization_id>/",
        views.OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    path(
        "organizations/<uuid:organization_id>/members/",
        views.MembershipListCreateView.as_view(),
        name="membership-list-create",
    ),
    path(
        "organizations/<uuid:organization_id>/members/<uuid:membership_id>/role/",
        views.MembershipRoleAssignView.as_view(),
        name="membership-role-assign",
    ),
    path(
        "organizations/<uuid:organization_id>/members/<uuid:membership_id>/roles/<slug:role_slug>/",
        views.MembershipRoleRemoveView.as_view(),
        name="membership-role-remove",
    ),
    path(
        "organizations/<uuid:organization_id>/roles/",
        views.OrganizationRolesView.as_view(),
        name="organization-roles",
    ),
    path(
        "organizations/<uuid:organization_id>/teams/",
        views.TeamListCreateView.as_view(),
        name="team-list-create",
    ),
    path(
        "teams/<uuid:team_id>/members/",
        views.TeamMemberListCreateView.as_view(),
        name="team-member-list-create",
    ),
    path(
        "teams/<uuid:team_id>/members/<uuid:user_id>/",
        views.TeamMemberDetailView.as_view(),
        name="team-member-detail",
    ),
]
