from django.urls import path

from . import backup_views, views

urlpatterns = [
    path("system/version/", views.VersionView.as_view(), name="system-version"),
    path("system/backups/", backup_views.BackupListView.as_view(), name="system-backups"),
    path("system/backups/run/", backup_views.BackupRunView.as_view(), name="system-backups-run"),
]
