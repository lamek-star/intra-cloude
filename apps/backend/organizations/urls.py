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
]
