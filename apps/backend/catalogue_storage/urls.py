from django.urls import path

from . import views

urlpatterns = [
    path("catalogue/oem-parts/", views.OEMPartSearchView.as_view(), name="oem-part-search"),
    path("catalogue/oem-parts/import/", views.OEMPartImportView.as_view(), name="oem-part-import"),
    path("catalogue/oem-parts/<uuid:part_id>/", views.OEMPartDetailView.as_view(), name="oem-part-detail"),
    path("catalogue/diagrams/<uuid:diagram_id>/image/", views.DiagramImageView.as_view(), name="diagram-image"),
]
