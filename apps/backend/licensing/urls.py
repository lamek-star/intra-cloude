from django.urls import path

from . import views

urlpatterns = [
    path("license/", views.LicenceView.as_view(), name="licence"),
    path("license/activate/", views.ActivateView.as_view(), name="licence-activate"),
]
