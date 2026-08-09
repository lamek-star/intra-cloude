from django.urls import path

from . import views

urlpatterns = [
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
