from django.urls import path

from . import views

urlpatterns = [
    path("organizations/<uuid:organization_id>/app-templates/", views.TemplateList.as_view()),
    path("app-templates/<uuid:object_id>/", views.TemplateDetail.as_view()),
    path("app-templates/<uuid:object_id>/versions/", views.VersionList.as_view()),
    path("app-template-versions/<uuid:object_id>/", views.VersionDetail.as_view()),
    path("projects/<uuid:project_id>/app-instances/", views.InstanceList.as_view()),
    path("app-instances/<uuid:object_id>/", views.InstanceDetail.as_view()),
    path("app-instances/<uuid:object_id>/models/", views.ModelList.as_view()),
    path("app-models/<uuid:object_id>/", views.DefinitionDetail.as_view()),
    path("app-models/<uuid:object_id>/fields/", views.FieldList.as_view()),
    path("app-fields/<uuid:object_id>/", views.FieldDetail.as_view()),
    path("app-instances/<uuid:object_id>/relationships/", views.RelationshipList.as_view()),
    path("app-relationships/<uuid:object_id>/", views.RelationshipDetail.as_view()),
]
