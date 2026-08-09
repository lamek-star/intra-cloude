from django.urls import path

from . import views

urlpatterns = [
    path(
        "organizations/<uuid:organization_id>/audit/",
        views.AuditEventListView.as_view(),
        name="audit-event-list",
    ),
]
