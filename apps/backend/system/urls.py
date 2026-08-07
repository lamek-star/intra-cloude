from django.urls import path

from . import views

urlpatterns = [
    path("healthz", views.HealthzView.as_view(), name="healthz"),
    path("readyz", views.ReadyzView.as_view(), name="readyz"),
]
