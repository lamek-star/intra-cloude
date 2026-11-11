from django.urls import path

from . import views

urlpatterns = [
    path(
        "organizations/<uuid:organization_id>/units/",
        views.OrganizationalUnitListCreateView.as_view(),
        name="org-unit-list-create",
    ),
    path(
        "organizations/<uuid:organization_id>/units/tree/",
        views.OrganizationalUnitTreeView.as_view(),
        name="org-unit-tree",
    ),
    path("units/<uuid:unit_id>/", views.OrganizationalUnitDetailView.as_view(), name="org-unit-detail"),
    path(
        "units/<uuid:unit_id>/members/",
        views.UnitMemberListCreateView.as_view(),
        name="org-unit-member-list-create",
    ),
    path(
        "units/<uuid:unit_id>/members/<uuid:user_id>/",
        views.UnitMemberDetailView.as_view(),
        name="org-unit-member-detail",
    ),
]
