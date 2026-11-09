from django.urls import path

from . import views

urlpatterns = [
    path("system/version/", views.VersionView.as_view(), name="system-version"),
]
