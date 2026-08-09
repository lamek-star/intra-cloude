from django.urls import path

from . import views

urlpatterns = [
    path(
        "projects/<uuid:project_id>/tenant-databases/",
        views.TenantDatabaseListCreateView.as_view(),
        name="tenant-database-list-create",
    ),
    path(
        "tenant-databases/<uuid:tenant_database_id>/",
        views.TenantDatabaseDetailView.as_view(),
        name="tenant-database-detail",
    ),
    path(
        "tenant-databases/<uuid:tenant_database_id>/tables/",
        views.TableListCreateView.as_view(),
        name="table-list-create",
    ),
    path("tables/<uuid:table_id>/", views.TableDetailView.as_view(), name="table-detail"),
    path("tables/<uuid:table_id>/columns/", views.ColumnCreateView.as_view(), name="column-create"),
    path(
        "tables/<uuid:table_id>/foreign-keys/",
        views.ForeignKeyCreateView.as_view(),
        name="foreign-key-create",
    ),
    path("tables/<uuid:table_id>/rows/export/", views.RowExportView.as_view(), name="row-export"),
    path("tables/<uuid:table_id>/rows/", views.RowListCreateView.as_view(), name="row-list-create"),
    path("tables/<uuid:table_id>/rows/<uuid:row_id>/", views.RowDetailView.as_view(), name="row-detail"),
]
