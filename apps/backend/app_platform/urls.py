from django.urls import path

from . import attachment_views, record_views, runtime_views, upgrade_views, views

urlpatterns = [
    path("app-instances/<uuid:object_id>/runtime/", runtime_views.Runtime.as_view()),
    path("app-instances/<uuid:object_id>/runtime-plan/", runtime_views.RuntimePlan.as_view()),
    path("organizations/<uuid:organization_id>/app-templates/", views.TemplateList.as_view()),
    path("app-templates/<uuid:object_id>/", views.TemplateDetail.as_view()),
    path("app-templates/<uuid:object_id>/versions/", views.VersionList.as_view()),
    path("app-template-versions/<uuid:object_id>/", views.VersionDetail.as_view()),
    path("projects/<uuid:project_id>/app-instances/", views.InstanceList.as_view()),
    path("app-instances/<uuid:object_id>/", views.InstanceDetail.as_view()),
    path("app-instances/<uuid:object_id>/models/", views.ModelList.as_view()),
    path("app-models/<uuid:object_id>/", views.DefinitionDetail.as_view()),
    path("app-models/<uuid:object_id>/fields/", views.FieldList.as_view()),
    path("app-models/<uuid:object_id>/constraints/", views.ConstraintList.as_view()),
    path("app-constraints/<uuid:object_id>/", views.ConstraintDetail.as_view()),
    path("app-models/<uuid:object_id>/records/", record_views.RecordListCreateView.as_view()),
    path("app-models/<uuid:object_id>/records/<uuid:record_id>/", record_views.RecordDetailView.as_view()),
    path(
        "app-models/<uuid:object_id>/records/<uuid:record_id>/attachments/",
        attachment_views.AttachmentListCreateView.as_view(),
    ),
    path(
        "app-models/<uuid:object_id>/records/<uuid:record_id>/attachments/<uuid:attachment_id>/",
        attachment_views.AttachmentDetailView.as_view(),
    ),
    path(
        "app-models/<uuid:object_id>/records/<uuid:record_id>/attachments/<uuid:attachment_id>/download/",
        attachment_views.AttachmentDownloadView.as_view(),
    ),
    path("app-fields/<uuid:object_id>/", views.FieldDetail.as_view()),
    path("app-fields/<uuid:object_id>/unique/", views.FieldUniqueView.as_view()),
    path("app-fields/<uuid:object_id>/indexed/", views.FieldIndexedView.as_view()),
    path("app-instances/<uuid:object_id>/relationships/", views.RelationshipList.as_view()),
    path("app-instances/<uuid:object_id>/quantity-ledgers/", views.QuantityLedgerList.as_view()),
    path("app-instances/<uuid:object_id>/transactions/", record_views.TransactionView.as_view()),
    path("app-relationships/<uuid:object_id>/", views.RelationshipDetail.as_view()),
    path("app-models/<uuid:object_id>/workflows/", views.WorkflowList.as_view()),
    path("app-workflows/<uuid:object_id>/", views.WorkflowDetail.as_view()),
    path("app-workflows/<uuid:object_id>/states/", views.StateList.as_view()),
    path("app-workflow-states/<uuid:object_id>/", views.StateDetail.as_view()),
    path("app-workflows/<uuid:object_id>/transitions/", views.TransitionList.as_view()),
    path("app-transitions/<uuid:object_id>/", views.TransitionDetail.as_view()),
    path(
        "app-models/<uuid:object_id>/records/<uuid:record_id>/transitions/<uuid:transition_id>/apply/",
        views.ApplyTransitionView.as_view(),
    ),
    path("app-models/<uuid:object_id>/unit-grants/", views.UnitScopeGrantList.as_view()),
    path("app-unit-grants/<uuid:object_id>/", views.UnitScopeGrantDetail.as_view()),
    path(
        "app-instances/<uuid:object_id>/upgrade/<uuid:version_id>/",
        upgrade_views.UpgradeView.as_view(),
    ),
    path("app-instances/<uuid:object_id>/upgrades/", upgrade_views.UpgradeHistoryList.as_view()),
]
