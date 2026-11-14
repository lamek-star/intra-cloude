# Reference A — the API

Every endpoint, generated from the URL configuration and the views' own descriptions. Paths under `api/v1/` need a signed-in session (or an application's bearer credential where the view allows it); each view checks its capability itself (see Chapter 4). `<uuid:...>` is an id.

## accounts

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/auth/csrf/` | GET | `CSRFView` | `GET /auth/csrf/` — a browser SPA hits this once on load so Django actually sets the `csrftoken` cookie (it's otherwise only set as a side effect of `get_token()` running during some other request, e.g. the first authenticated mutation, which is too late — the |
| `/api/v1/auth/login/` | POST | `LoginView` |  |
| `/api/v1/auth/logout/` | POST | `LogoutView` |  |
| `/api/v1/auth/me/` | GET | `MeView` |  |
| `/api/v1/auth/mfa/confirm/` | POST | `MFAConfirmView` |  |
| `/api/v1/auth/mfa/disable/` | POST | `MFADisableView` |  |
| `/api/v1/auth/mfa/enroll/` | POST | `MFAEnrollView` |  |
| `/api/v1/auth/mfa/recovery-codes/` | GET, POST | `MFARecoveryCodesView` | GET: how many recovery codes are left. POST (a current 6-digit code): 10 new ones, the old ones gone. |
| `/api/v1/auth/mfa/verify/` | POST | `MFALoginVerifyView` |  |
| `/api/v1/auth/passkeys/` | GET | `PasskeyListView` | `GET /auth/passkeys/` -- the signed-in user's own passkeys (never anyone else's). |
| `/api/v1/auth/passkeys/<uuid:passkey_id>/remove/` | POST | `PasskeyRemoveView` |  |
| `/api/v1/auth/passkeys/check/options/` | POST | `PasskeyCheckOptionsView` | Signed in: a fresh check with one of the user's own passkeys. Signed out: passkey sign-in. |
| `/api/v1/auth/passkeys/check/verify/` | POST | `PasskeyCheckVerifyView` |  |
| `/api/v1/auth/passkeys/only/` | POST | `PasskeyOnlyView` | `POST /auth/passkeys/only/` with `{"on": true, "password": ...}`, or `{"on": false}` after a fresh passkey check in this session. |
| `/api/v1/auth/passkeys/register/options/` | POST | `PasskeyRegisterOptionsView` |  |
| `/api/v1/auth/passkeys/register/verify/` | POST | `PasskeyRegisterVerifyView` |  |
| `/api/v1/auth/password/` | POST | `PasswordChangeView` | The person changes their own password (their current one, then a new one). Their session stays signed in. |
| `/api/v1/auth/register/` | POST | `RegisterView` |  |

## analytics

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/dashboards/<uuid:dashboard_id>/` | GET, PATCH, DELETE | `DashboardDetailView` |  |
| `/api/v1/dashboards/<uuid:dashboard_id>/render/` | GET | `DashboardRenderView` |  |
| `/api/v1/tables/<uuid:table_id>/analyze/` | POST | `TableAnalyzeView` |  |
| `/api/v1/tables/<uuid:table_id>/profile/` | GET | `TableProfileView` |  |
| `/api/v1/tenant-databases/<uuid:tenant_database_id>/dashboards/` | GET, POST | `DashboardListCreateView` |  |

## app_platform

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/app-constraints/<uuid:object_id>/` | GET, PATCH | `ConstraintDetail` |  |
| `/api/v1/app-fields/<uuid:object_id>/` | GET, PATCH | `FieldDetail` |  |
| `/api/v1/app-fields/<uuid:object_id>/indexed/` | POST | `FieldIndexedView` |  |
| `/api/v1/app-fields/<uuid:object_id>/unique/` | POST | `FieldUniqueView` | Dedicated action, human-session-only (schema mutation stays out of this first bearer-token slice -- see FoundationView's own docstring): retrofits a UNIQUE constraint onto an existing field, safely against an already-provisioned, possibly populated runtime. |
| `/api/v1/app-instances/<uuid:object_id>/` | GET, PATCH | `InstanceDetail` |  |
| `/api/v1/app-instances/<uuid:object_id>/built-in/retry/` | POST | `BuiltInAppRetry` | Finish preparing a built-in application whose setup did not complete. Idempotent. |
| `/api/v1/app-instances/<uuid:object_id>/models/` | GET, POST | `ModelList` |  |
| `/api/v1/app-instances/<uuid:object_id>/operations/receive/` | POST | `ReceiveView` |  |
| `/api/v1/app-instances/<uuid:object_id>/operations/sell/` | POST | `SellView` |  |
| `/api/v1/app-instances/<uuid:object_id>/quantity-ledgers/` | GET, POST | `QuantityLedgerList` |  |
| `/api/v1/app-instances/<uuid:object_id>/relationships/` | GET, POST | `RelationshipList` |  |
| `/api/v1/app-instances/<uuid:object_id>/runtime-plan/` | GET | `RuntimePlan` |  |
| `/api/v1/app-instances/<uuid:object_id>/runtime/` | GET, POST | `Runtime` |  |
| `/api/v1/app-instances/<uuid:object_id>/schema/` | GET | `InstanceSchema` | An instance's whole schema -- every model with its fields, and every relationship -- in ONE read-only request and a constant number of queries. A client that needs the schema (the customer screens resolve model/field/relationship ids from it) would otherwise i |
| `/api/v1/app-instances/<uuid:object_id>/transactions/` | POST | `TransactionView` | Several record operations committed as one unit (transactions.py). Human session only: no `service_account_methods`, so an external bearer- token client keeps using ordinary single-record CRUD. Authorization is per operation, inside transactions.run -> records |
| `/api/v1/app-instances/<uuid:object_id>/upgrade/<uuid:version_id>/` | GET, POST | `UpgradeView` | GET previews a three-way diff against a target template version without changing anything; POST applies it (additions and safe label syncs only -- see upgrades.py for exactly what "safe" means and why). Human-session-only: an upgrade is schema administration,  |
| `/api/v1/app-instances/<uuid:object_id>/upgrades/` | GET | `UpgradeHistoryList` |  |
| `/api/v1/app-models/<uuid:object_id>/` | GET, PATCH | `DefinitionDetail` |  |
| `/api/v1/app-models/<uuid:object_id>/constraints/` | GET, POST | `ConstraintList` |  |
| `/api/v1/app-models/<uuid:object_id>/fields/` | GET, POST | `FieldList` |  |
| `/api/v1/app-models/<uuid:object_id>/records/` | GET, POST | `RecordListCreateView` |  |
| `/api/v1/app-models/<uuid:object_id>/records/<uuid:record_id>/` | GET, PATCH, DELETE | `RecordDetailView` |  |
| `/api/v1/app-models/<uuid:object_id>/records/<uuid:record_id>/attachments/` | GET, POST | `AttachmentListCreateView` |  |
| `/api/v1/app-models/<uuid:object_id>/records/<uuid:record_id>/attachments/<uuid:attachment_id>/` | DELETE | `AttachmentDetailView` |  |
| `/api/v1/app-models/<uuid:object_id>/records/<uuid:record_id>/attachments/<uuid:attachment_id>/download/` | GET | `AttachmentDownloadView` |  |
| `/api/v1/app-models/<uuid:object_id>/records/<uuid:record_id>/transitions/<uuid:transition_id>/apply/` | POST | `ApplyTransitionView` | Applying a transition is fundamentally a record write -- open to a scoped bearer token the same way record CRUD already is (Phase 7), unlike every workflow *authoring* endpoint above, which stays human-only. All real authorization (database.write, plus app_ins |
| `/api/v1/app-models/<uuid:object_id>/unit-grants/` | GET, POST | `UnitScopeGrantList` | Phase 7 Step 3 ("unit scope"): an administrative sharing action, never something a bearer token needs to perform on its own behalf -- human-session-only, no service_account_methods opt-in. |
| `/api/v1/app-models/<uuid:object_id>/workflows/` | GET, POST | `WorkflowList` |  |
| `/api/v1/app-relationships/<uuid:object_id>/` | GET, PATCH | `RelationshipDetail` |  |
| `/api/v1/app-template-versions/<uuid:object_id>/` | GET | `VersionDetail` |  |
| `/api/v1/app-templates/<uuid:object_id>/` | GET, PATCH | `TemplateDetail` |  |
| `/api/v1/app-templates/<uuid:object_id>/versions/` | GET, POST | `VersionList` |  |
| `/api/v1/app-transitions/<uuid:object_id>/` | GET, PATCH | `TransitionDetail` |  |
| `/api/v1/app-unit-grants/<uuid:object_id>/` | DELETE | `UnitScopeGrantDetail` |  |
| `/api/v1/app-workflow-states/<uuid:object_id>/` | GET, PATCH | `StateDetail` |  |
| `/api/v1/app-workflows/<uuid:object_id>/` | GET, PATCH | `WorkflowDetail` |  |
| `/api/v1/app-workflows/<uuid:object_id>/states/` | GET, POST | `StateList` |  |
| `/api/v1/app-workflows/<uuid:object_id>/transitions/` | GET, POST | `TransitionList` |  |
| `/api/v1/built-in-apps/` | GET | `BuiltInAppList` | What this deployment offers a customer -- QUALIFIED applications only, unless SHOW_UNQUALIFIED_BUILT_IN_APPS is on. With `?project=<id>` each entry also lists the instances of it in that project the caller may read, and their runtime state. Human sessions only |
| `/api/v1/organizations/<uuid:organization_id>/app-templates/` | GET, POST | `TemplateList` |  |
| `/api/v1/projects/<uuid:project_id>/app-instances/` | GET, POST | `InstanceList` |  |
| `/api/v1/projects/<uuid:project_id>/built-in-apps/<str:key>/install/` | POST | `BuiltInAppInstall` | Install one built-in application into a project the caller is a member of. Authorization is unchanged: every underlying service checks its own capability. |

## applications

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/applications/<uuid:application_id>/` | GET | `ApplicationDetailView` |  |
| `/api/v1/applications/<uuid:application_id>/credentials/` | GET, POST | `ApplicationCredentialListCreateView` |  |
| `/api/v1/applications/<uuid:application_id>/credentials/<uuid:credential_id>/revoke/` | POST | `ApplicationCredentialRevokeView` |  |
| `/api/v1/applications/<uuid:application_id>/credentials/<uuid:credential_id>/rotate/` | POST | `ApplicationCredentialRotateView` |  |
| `/api/v1/applications/<uuid:application_id>/requests/` | GET | `ApplicationRequestLogView` | The application's recent requests (application.read): newest first, paginated; ?errors=1 shows only the ones that did not succeed (status 400 and above). |
| `/api/v1/applications/<uuid:application_id>/resource-grants/` | GET, POST | `ApplicationResourceGrantListCreateView` |  |
| `/api/v1/applications/<uuid:application_id>/resource-grants/<uuid:grant_id>/` | DELETE | `ApplicationResourceGrantDetailView` | Revokes one of the application's own grants (e.g. taking IntraForge Pay away from a hosted app). |
| `/api/v1/organizations/<uuid:organization_id>/applications/` | GET, POST | `ApplicationListCreateView` |  |

## audit

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/organizations/<uuid:organization_id>/audit/` | GET | `AuditEventListView` | Real filtering/pagination over the organization's full audit history — the previous implementation returned only the most recent 200 events with no way to reach anything older or narrow by action/ actor/date, which made it useless for an actual incident invest |

## catalogue_storage

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/catalogue/diagrams/<uuid:diagram_id>/` | GET | `DiagramDetailView` | `GET /api/v1/catalogue/diagrams/{id}/` -- the diagram plus its stored figure snapshot (every part number drawn on it), served from this database alone so it works with no external access. |
| `/api/v1/catalogue/diagrams/<uuid:diagram_id>/image/` | GET | `DiagramImageView` | `GET /api/v1/catalogue/diagrams/{id}/image/` — only ever serves a LOCALLY_STORED diagram's actual bytes (streamed through the backend, same reasoning as storage.views.FileDownloadView: the object storage endpoint is an internal Docker DNS name). An EXTERNAL_RE |
| `/api/v1/catalogue/diagrams/import/` | POST | `DiagramFigureImportView` | `POST /api/v1/catalogue/diagrams/import/` -- persists one whole figure (see services.import_figure). Same gate as OEMPartImportView: only an ApplicationCredential bearer token may write; metadata only, never image bytes. |
| `/api/v1/catalogue/oem-parts/` | GET | `OEMPartSearchView` | `GET /api/v1/catalogue/oem-parts/?q=<part number, any format>` — the one search this integration needs: exact match on the normalized part number (see services.search_part). Reachable by either a human session or this deployment's spare-parts ApplicationCreden |
| `/api/v1/catalogue/oem-parts/<uuid:part_id>/` | GET | `OEMPartDetailView` |  |
| `/api/v1/catalogue/oem-parts/import/` | POST | `OEMPartImportView` | `POST /api/v1/catalogue/oem-parts/import/` — lets an external, bearer-authenticated caller (the spare-parts backend, resolving a live provider lookup on a cache miss) persist exactly one part+ diagram+link, through the identical idempotent path the CSV importe |

## databases

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/connected-databases/<uuid:connected_database_id>/` | GET, DELETE | `ConnectedDatabaseDetailView` |  |
| `/api/v1/connected-databases/<uuid:connected_database_id>/schema/` | GET | `ConnectedDatabaseSchemaView` |  |
| `/api/v1/connected-databases/<uuid:connected_database_id>/tables/<str:table_name>/rows/` | GET | `ConnectedDatabaseTableRowsView` |  |
| `/api/v1/connected-databases/<uuid:connected_database_id>/test/` | POST | `ConnectedDatabaseTestView` |  |
| `/api/v1/organizations/<uuid:organization_id>/tenant-databases/` | GET | `OrganizationTenantDatabaseListView` | Every database in an organization the caller may read (database.read, role-wide or a grant on that database, the same check as each project's list), with how many tables it has. |
| `/api/v1/projects/<uuid:project_id>/connected-databases/` | GET, POST | `ConnectedDatabaseListCreateView` |  |
| `/api/v1/projects/<uuid:project_id>/tenant-databases/` | GET, POST | `TenantDatabaseListCreateView` |  |
| `/api/v1/tables/<uuid:table_id>/` | GET, DELETE | `TableDetailView` |  |
| `/api/v1/tables/<uuid:table_id>/columns/` | POST | `ColumnCreateView` |  |
| `/api/v1/tables/<uuid:table_id>/foreign-keys/` | GET, POST | `ForeignKeyCreateView` |  |
| `/api/v1/tables/<uuid:table_id>/rows/` | GET, POST | `RowListCreateView` |  |
| `/api/v1/tables/<uuid:table_id>/rows/<uuid:row_id>/` | GET, PATCH, DELETE | `RowDetailView` |  |
| `/api/v1/tables/<uuid:table_id>/rows/export/` | GET | `RowExportView` |  |
| `/api/v1/tenant-databases/<uuid:tenant_database_id>/` | GET, DELETE | `TenantDatabaseDetailView` |  |
| `/api/v1/tenant-databases/<uuid:tenant_database_id>/tables/` | GET, POST | `TableListCreateView` |  |

## environments

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/applications/<uuid:application_id>/environments/` | GET, POST | `EnvironmentListCreateView` |  |
| `/api/v1/environments/<uuid:environment_id>/` | GET, PATCH, DELETE | `EnvironmentDetailView` |  |
| `/api/v1/environments/<uuid:environment_id>/clone/` | POST | `EnvironmentCloneView` |  |
| `/api/v1/environments/<uuid:environment_id>/credentials/` | GET, POST | `EnvironmentCredentialListCreateView` |  |
| `/api/v1/environments/<uuid:environment_id>/credentials/<uuid:credential_id>/revoke/` | POST | `EnvironmentCredentialRevokeView` |  |
| `/api/v1/environments/<uuid:environment_id>/credentials/<uuid:credential_id>/rotate/` | POST | `EnvironmentCredentialRotateView` |  |
| `/api/v1/environments/<uuid:environment_id>/database/` | PATCH | `EnvironmentDatabaseBindingView` |  |
| `/api/v1/environments/<uuid:environment_id>/disable/` | POST | `EnvironmentDisableView` |  |
| `/api/v1/environments/<uuid:environment_id>/enable/` | POST | `EnvironmentEnableView` |  |
| `/api/v1/environments/<uuid:environment_id>/secrets/` | GET, POST | `EnvironmentSecretListCreateView` |  |
| `/api/v1/environments/<uuid:environment_id>/secrets/<uuid:secret_id>/` | DELETE | `EnvironmentSecretDetailView` |  |
| `/api/v1/environments/<uuid:environment_id>/secrets/<uuid:secret_id>/rotate/` | POST | `EnvironmentSecretRotateView` |  |
| `/api/v1/environments/<uuid:environment_id>/storage/` | PATCH | `EnvironmentStorageBindingView` |  |
| `/api/v1/environments/<uuid:environment_id>/variables/` | GET, POST | `EnvironmentVariableListCreateView` |  |
| `/api/v1/environments/<uuid:environment_id>/variables/<uuid:variable_id>/` | DELETE | `EnvironmentVariableDetailView` |  |
| `/api/v1/environments/<uuid:environment_id>/webhooks/` | GET, POST | `EnvironmentWebhookListCreateView` |  |
| `/api/v1/environments/<uuid:environment_id>/webhooks/<uuid:webhook_id>/` | PATCH, DELETE | `EnvironmentWebhookDetailView` |  |

## exports

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/export/<uuid:job_id>/` | GET | `ExportJobDetailView` |  |
| `/api/v1/export/<uuid:job_id>/download/` | GET | `ExportJobDownloadView` |  |
| `/api/v1/import/` | POST | `RestoreJobListCreateView` | Deliberately not organization-scoped in its URL — a restore creates a brand-new organization, so there is no existing one to nest this endpoint under (see services.stage_restore_upload). |
| `/api/v1/import/<uuid:job_id>/` | GET | `RestoreJobDetailView` |  |
| `/api/v1/organizations/<uuid:organization_id>/export/` | GET, POST | `ExportJobListCreateView` |  |

## imports

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/files/<uuid:file_id>/import-preview/` | GET | `ImportPreviewView` |  |
| `/api/v1/imports/<uuid:job_id>/` | GET | `ImportJobDetailView` |  |
| `/api/v1/imports/<uuid:job_id>/errors/` | GET | `ImportJobErrorListView` |  |
| `/api/v1/tables/<uuid:table_id>/imports/` | GET, POST | `ImportJobListCreateView` |  |

## licensing

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/license/` | GET | `LicenceView` |  |
| `/api/v1/license/activate/` | POST | `ActivateView` |  |

## movie_shop

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/movie-ads/<uuid:ad_id>/` | PATCH, DELETE | `AdDetailView` |  |
| `/api/v1/movie-ads/<uuid:ad_id>/picture/` | GET, POST | `AdPictureView` |  |
| `/api/v1/movie-agent/copies/<uuid:line_id>/` | POST | `AgentCopyProgressView` |  |
| `/api/v1/movie-agent/libraries/<uuid:library_id>/covers/` | POST | `AgentCoverView` |  |
| `/api/v1/movie-agent/libraries/<uuid:library_id>/scan/finish/` | POST | `AgentScanFinishView` |  |
| `/api/v1/movie-agent/libraries/<uuid:library_id>/scan/start/` | POST | `AgentScanStartView` |  |
| `/api/v1/movie-agent/libraries/<uuid:library_id>/scan/titles/` | POST | `AgentScanTitlesView` |  |
| `/api/v1/movie-agent/report/` | POST | `AgentReportView` |  |
| `/api/v1/movie-customers/<uuid:customer_id>/` | PATCH | `CustomerDetailView` |  |
| `/api/v1/movie-customers/<uuid:customer_id>/approve/` | POST | `CustomerActionView` |  |
| `/api/v1/movie-customers/<uuid:customer_id>/block/` | POST | `CustomerActionView` |  |
| `/api/v1/movie-customers/<uuid:customer_id>/points/` | POST | `CustomerPointsView` |  |
| `/api/v1/movie-customers/<uuid:customer_id>/reject/` | POST | `CustomerActionView` |  |
| `/api/v1/movie-customers/<uuid:customer_id>/reset-code/` | POST | `CustomerActionView` |  |
| `/api/v1/movie-customers/<uuid:customer_id>/unblock/` | POST | `CustomerActionView` |  |
| `/api/v1/movie-customers/<uuid:customer_id>/wallet-password/` | POST | `CustomerActionView` |  |
| `/api/v1/movie-libraries/<uuid:library_id>/` | PATCH, DELETE | `LibraryDetailView` |  |
| `/api/v1/movie-libraries/<uuid:library_id>/scan/` | POST | `LibraryScanView` |  |
| `/api/v1/movie-sales/<uuid:sale_id>/` | GET | `SaleDetailView` |  |
| `/api/v1/movie-sales/<uuid:sale_id>/cancel/` | POST | `SaleActionView` |  |
| `/api/v1/movie-sales/<uuid:sale_id>/cash/` | POST | `SaleActionView` |  |
| `/api/v1/movie-sales/<uuid:sale_id>/charge/` | POST | `SaleChargeView` | The counter charges a portal order: the customer's drive, IF Pay or cash; their rewards apply now. |
| `/api/v1/movie-sales/<uuid:sale_id>/retry/` | POST | `SaleActionView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/` | GET, PATCH | `ShopDetailView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/ads/` | GET, POST | `AdListCreateView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/agent-credential/` | POST | `AgentCredentialView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/categories/` | GET | `CategoryListView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/counter-customers/` | GET | `CounterCustomerFindView` | For the person at the counter (movies.sell): finds an approved portal customer by phone number, to apply their rewards to a counter sale. Deliberately narrow: at least 6 digits of the number, at most 5 matches, the name, the number's last 4 digits and the poin |
| `/api/v1/movie-shops/<uuid:shop_id>/customers/` | GET | `CustomerListView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/destinations/` | GET | `DestinationsView` | The drives a sold title can be copied to (what the media agent sees now), for the person at the counter. |
| `/api/v1/movie-shops/<uuid:shop_id>/drives/` | GET | `DrivesView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/libraries/` | GET, POST | `LibraryListCreateView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/portal/` | GET, PUT | `PortalSettingsView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/prices/` | PUT | `ShopPricesView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/sales/` | GET, POST | `SaleListCreateView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/titles/` | GET | `TitleListView` |  |
| `/api/v1/movie-shops/<uuid:shop_id>/today/` | GET | `ShopTodayView` | The shop's day so far, for the catalogue's "Today" card: titles sold, credits taken and new portal customers since ``since`` (the browser's own midnight, so the day is the shop's, not UTC's). |
| `/api/v1/movie-titles/<uuid:title_id>/` | PATCH | `TitleDetailView` |  |
| `/api/v1/movie-titles/<uuid:title_id>/cover/` | GET, POST, DELETE | `TitleCoverView` |  |
| `/api/v1/organizations/<uuid:organization_id>/movie-shops/` | GET, POST | `ShopListCreateView` |  |
| `/api/v1/portal/` | GET | `PortalDirectoryView` | The shop's open portals, for the short address on the shop network (https://movies.lan:8443 opens /portal/): just their names, so a phone can pick one. Nothing else about a shop is shown. |
| `/api/v1/portal/<shop_id>/` | GET | `PortalHomeView` |  |
| `/api/v1/portal/<shop_id>/ads/` | GET | `PortalAdsView` |  |
| `/api/v1/portal/<shop_id>/ads/<ad_id>/picture/` | GET | `PortalAdPictureView` |  |
| `/api/v1/portal/<shop_id>/ads/<ad_id>/tap/` | POST | `PortalAdTapView` |  |
| `/api/v1/portal/<shop_id>/categories/` | GET | `PortalCategoriesView` |  |
| `/api/v1/portal/<shop_id>/forgot/` | POST | `PortalForgotView` | "I forgot my password": the owner is asked, and gives the customer a one-time code at the counter. |
| `/api/v1/portal/<shop_id>/login/` | POST | `PortalSignInView` |  |
| `/api/v1/portal/<shop_id>/logout/` | POST | `PortalSignOutView` |  |
| `/api/v1/portal/<shop_id>/me/` | GET | `PortalMeView` |  |
| `/api/v1/portal/<shop_id>/orders/` | GET, POST | `PortalOrdersView` |  |
| `/api/v1/portal/<shop_id>/orders/<sale_id>/cancel/` | POST | `PortalOrderCancelView` |  |
| `/api/v1/portal/<shop_id>/reset/` | POST | `PortalResetView` |  |
| `/api/v1/portal/<shop_id>/signup/` | POST | `PortalSignUpView` |  |
| `/api/v1/portal/<shop_id>/titles/` | GET | `PortalTitlesView` |  |
| `/api/v1/portal/<shop_id>/titles/<title_id>/` | GET | `PortalTitleView` |  |
| `/api/v1/portal/<shop_id>/titles/<title_id>/cover/` | GET | `PortalCoverView` |  |

## oauth_provider

| Path | Methods | View | What it does |
|---|---|---|---|
| `/.well-known/openid-configuration` | GET | `OpenIDConfigurationView` |  |
| `/api/v1/oauth-clients/` | GET, POST | `OAuthClientListCreateView` |  |
| `/api/v1/oauth-clients/<uuid:client_pk>/` | GET, PATCH | `OAuthClientDetailView` |  |
| `/api/v1/oauth-clients/<uuid:client_pk>/rotate-secret/` | POST | `OAuthClientRotateSecretView` |  |
| `/api/v1/oauth/consent/` | GET, POST | `ConsentView` | The consent screen's API (session only). GET says which application asks for what; POST records Allow (the screen then goes back to /oauth/authorize) or Deny (the answer is the application's redirect_uri with error=access_denied, built here only after redirect |
| `/oauth/authorize` | GET | `AuthorizeView` | `GET /oauth/authorize` — RFC 6749 Section 4.1.1 / OIDC Core Section 3.1.2.1. Reuses the *existing* session-cookie login/register pages verbatim for the "user must authenticate" step (redirecting to `/login?next=<this-request>`, which already round-trips throug |
| `/oauth/jwks.json` | GET | `JWKSView` |  |
| `/oauth/revoke` | POST | `RevokeView` | `POST /oauth/revoke` — RFC 7009. Always 200 regardless of whether the token existed/was already revoked (Section 2.2: don't let the response distinguish an invalid token from a successfully revoked one). |
| `/oauth/token` | POST | `TokenView` | `POST /oauth/token` — server-to-server (the spare-parts Next.js backend, never the browser). Accepts the client credentials in the POST body (widely supported alongside HTTP Basic; simpler for a fetch()-based caller) rather than requiring Basic auth. |
| `/oauth/userinfo` | GET | `UserInfoView` | `GET /oauth/userinfo` — OIDC Core Section 5.3. Bearer-token authenticated independently of DRF's configured authentication classes (this token is this app's own opaque OAuthAccessToken, not a Django session or an ApplicationCredential). `authentication_classes |

## org_units

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/organizations/<uuid:organization_id>/units/` | GET, POST | `OrganizationalUnitListCreateView` |  |
| `/api/v1/organizations/<uuid:organization_id>/units/tree/` | GET | `OrganizationalUnitTreeView` |  |
| `/api/v1/units/<uuid:unit_id>/` | GET, PATCH, DELETE | `OrganizationalUnitDetailView` |  |
| `/api/v1/units/<uuid:unit_id>/members/` | GET, POST | `UnitMemberListCreateView` |  |
| `/api/v1/units/<uuid:unit_id>/members/<uuid:user_id>/` | DELETE | `UnitMemberDetailView` |  |

## organizations

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/organizations/` | GET, POST | `OrganizationListCreateView` |  |
| `/api/v1/organizations/<uuid:organization_id>/` | GET | `OrganizationDetailView` |  |
| `/api/v1/organizations/<uuid:organization_id>/members/` | GET, POST | `MembershipListCreateView` |  |
| `/api/v1/organizations/<uuid:organization_id>/members/<uuid:membership_id>/reset-password/` | POST | `MembershipPasswordResetView` | An administrator gives a staff member a temporary password (shown once) when they forgot theirs: users.manage here, and in every other organization the person belongs to (accounts.services.can_reset_password). The person is signed out everywhere and must choos |
| `/api/v1/organizations/<uuid:organization_id>/members/<uuid:membership_id>/role/` | POST | `MembershipRoleAssignView` |  |
| `/api/v1/organizations/<uuid:organization_id>/members/<uuid:membership_id>/roles/<slug:role_slug>/` | DELETE | `MembershipRoleRemoveView` |  |
| `/api/v1/organizations/<uuid:organization_id>/roles/` | GET | `OrganizationRolesView` | The roles this organization can give its members, and who holds which. Only for people who may manage roles (permissions.manage): who has which role is not shown to every member. |
| `/api/v1/organizations/<uuid:organization_id>/teams/` | GET, POST | `TeamListCreateView` |  |
| `/api/v1/teams/<uuid:team_id>/members/` | POST | `TeamMemberListCreateView` |  |
| `/api/v1/teams/<uuid:team_id>/members/<uuid:user_id>/` | DELETE | `TeamMemberDetailView` |  |

## service_apps

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/internal/service-apps/audit-events/` | POST | `InternalAuditView` |  |
| `/api/v1/internal/service-apps/config/` | GET, PATCH | `InternalConfigView` |  |
| `/api/v1/internal/service-apps/files/` | POST | `InternalFilesView` |  |
| `/api/v1/internal/service-apps/files/<uuid:file_id>/` | GET, DELETE | `InternalFileDetailView` |  |
| `/api/v1/internal/service-apps/heartbeat/` | POST | `InternalHeartbeatView` |  |
| `/api/v1/internal/service-apps/pay/payment-requests/` | POST | `InternalPayRequestsView` | Ask this shop's IntraForge Pay to take a payment (pay_bridge.py): the caller names the person, the amount, what it is for and its own record; IntraForge picks the Pay and checks the person. |
| `/api/v1/internal/service-apps/pay/payment-requests/<uuid:request_id>/` | GET | `InternalPayRequestDetailView` |  |
| `/api/v1/internal/service-apps/self/` | GET | `InternalSelfView` |  |
| `/api/v1/internal/service-apps/sessions/introspect/` | POST | `InternalIntrospectView` |  |
| `/api/v1/internal/service-apps/sessions/revoke/` | POST | `InternalRevokeView` |  |
| `/api/v1/internal/service-apps/users/` | GET | `InternalUsersView` |  |
| `/api/v1/pay/payment-requests/` | POST | `AppPayRequestsView` |  |
| `/api/v1/pay/payment-requests/<uuid:request_id>/` | GET | `AppPayRequestDetailView` |  |
| `/api/v1/service-apps/` | GET, POST | `ServiceAppListView` |  |
| `/api/v1/service-apps/<uuid:app_id>/` | GET, PATCH, DELETE | `ServiceAppDetailView` |  |
| `/api/v1/service-apps/<uuid:app_id>/launch/` | POST | `ServiceAppLaunchView` | "Open": mints an application session bound to this IntraForge login and sets it as an HttpOnly, SameSite=Strict cookie on the application's path. Nothing goes in the URL. |
| `/api/v1/service-apps/<uuid:app_id>/reinstate/` | POST | `ServiceAppReinstateView` |  |
| `/api/v1/service-apps/<uuid:app_id>/removal-preview/` | GET | `ServiceAppRemovalPreviewView` | What removing would affect (counts only), so the confirmation can say exactly what goes. |
| `/api/v1/service-apps/<uuid:app_id>/sign-in/` | GET | `ServiceAppSignInInfoView` | What the sign-in page shows when an application sent someone there ("Sign in to Spare Parts -- <shop>"). Public, but only what the application itself already shows before sign-in: its product name and shop name. Unknown, disabled or removed instances are a pla |

## sharing

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/organizations/<uuid:organization_id>/external-sharing/` | PATCH | `ExternalSharingSettingView` |  |
| `/api/v1/organizations/<uuid:organization_id>/shares/` | GET, POST | `ShareGrantListCreateView` |  |
| `/api/v1/shares/<uuid:share_id>/` | GET, DELETE | `ShareGrantDetailView` |  |

## sites

| Path | Methods | View | What it does |
|---|---|---|---|
| `/_sites-certificate/` | - | `certificate_allowed` | The proxy asks before it issues a certificate for a name (on-demand TLS): an online site's own name, or one of IntraForge's own names (OWN_TLS_HOSTNAMES), gets one. The proxy already serves IntraForge's names with its internal certificate; it also asks here wh |
| `/_sites/` | - | `sites_index` | The bare sites port and anything that is not a site address. No list of sites is given out. |
| `/_sites/^(?P<path>.*)$` | - | `sites_index` | The bare sites port and anything that is not a site address. No list of sites is given out. |
| `/_sites/^(?P<slug>[a-z0-9-]{1,50})$` | - | `site_root` | `/<slug>` without the slash: relative links in index.html need the slash. |
| `/_sites/^(?P<slug>[a-z0-9-]{1,50})/(?P<path>.*)$` | - | `serve_site` |  |
| `/_sites/^_host/(?P<path>.*)$` | - | `serve_by_host` | A site under its own name (https://<name>:<sites port>/...): the proxy says which name was asked for. |
| `/_sites/^_internet/(?P<path>.*)$` | - | `serve_internet` | A site published to the internet, reached through the tunnel and the proxy's internet listener only while the gate is on (ADR-0020 decision 4). |
| `/api/v1/internet-gateway/` | GET | `InternetGatewayView` | The gate's state. Everyone signed in may see whether it is on; only the Super Administrator sees the tunnel and what is published. |
| `/api/v1/internet-gateway/auto-publish/` | POST | `InternetAutoPublishView` | Auto-publish under a domain ({"domain": "harmongt.uk", "password": ...}), or off ({"domain": ""}). |
| `/api/v1/internet-gateway/disable/` | POST | `InternetGatewayDisableView` |  |
| `/api/v1/internet-gateway/enable/` | POST | `InternetGatewayEnableView` |  |
| `/api/v1/organizations/<uuid:organization_id>/sites/` | GET, POST | `SiteListCreateView` |  |
| `/api/v1/sites/<uuid:site_id>/` | GET, PATCH, DELETE | `SiteDetailView` |  |
| `/api/v1/sites/<uuid:site_id>/internet/` | POST, DELETE | `SiteInternetView` | Publish a site under a public name, or revoke it. The Super Administrator acts platform-wide, so the site is looked up directly -- but only for them; anyone else is refused before any lookup. |
| `/api/v1/sites/<uuid:site_id>/logs/` | GET | `SiteLogsView` | A server app's own output, its last 200 lines (sites.manage: an app's log can hold what its settings hold, so reading the site is not enough). |
| `/api/v1/sites/<uuid:site_id>/versions/` | GET, POST | `SiteVersionListCreateView` |  |
| `/api/v1/sites/<uuid:site_id>/versions/<uuid:version_id>/` | DELETE | `SiteVersionDetailView` |  |
| `/api/v1/sites/<uuid:site_id>/versions/<uuid:version_id>/activate/` | POST | `SiteVersionActivateView` |  |

## storage

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/buckets/<uuid:bucket_id>/` | GET, PATCH | `BucketDetailView` | One bucket's name and project, for a page opened straight from its address (a bookmark, a refresh): the same checks as listing its files. |
| `/api/v1/buckets/<uuid:bucket_id>/files/` | GET, POST | `FileListCreateView` |  |
| `/api/v1/buckets/<uuid:bucket_id>/folders/` | GET, POST | `FolderListCreateView` |  |
| `/api/v1/files/<uuid:file_id>/` | GET, PATCH, DELETE | `FileDetailView` |  |
| `/api/v1/files/<uuid:file_id>/download/` | GET | `FileDownloadView` | Streams the file through the backend rather than issuing a presigned URL directly to MinIO — OBJECT_STORAGE_ENDPOINT is an internal Docker DNS name, unreachable from a browser outside the Docker network in this deployment topology. See storage/backends.py:Obje |
| `/api/v1/files/<uuid:file_id>/restore/` | POST | `FileRestoreView` |  |
| `/api/v1/files/<uuid:file_id>/share-links/` | GET, POST | `FileShareLinkListCreateView` | A file's share links (storage.share on its bucket). POST {days, max_downloads?} makes one; its address is in that answer only. |
| `/api/v1/files/<uuid:file_id>/versions/` | GET, POST | `FileVersionUploadView` |  |
| `/api/v1/files/<uuid:file_id>/versions/<uuid:version_id>/download/` | GET | `FileVersionDownloadView` | Downloads one kept earlier content of a file (storage.read), streamed like the current one. |
| `/api/v1/files/<uuid:file_id>/versions/<uuid:version_id>/restore/` | POST | `FileVersionRestoreView` | Makes an earlier content the current one (storage.write); the replaced content is kept. |
| `/api/v1/organizations/<uuid:organization_id>/buckets/` | GET | `OrganizationBucketListView` | Every bucket in an organization the caller may read (storage.read, role-wide or a grant on that bucket, the same check as each project's list), with what it holds: files in use, their bytes, the bytes of kept earlier versions, and the Trash. For the organizati |
| `/api/v1/projects/<uuid:project_id>/buckets/` | GET, POST | `BucketListCreateView` |  |
| `/api/v1/share-links/<uuid:link_id>/revoke/` | POST | `FileShareLinkRevokeView` |  |
| `/api/v1/share/<str:token>/` | GET | `PublicShareView` | What a share link opens, for anyone who has it: the file's name and size (GET), or the file itself (download/). Nothing else about the organization is shown; a link that does not work is a plain 404. |
| `/api/v1/share/<str:token>/download/` | GET | `PublicShareView` | What a share link opens, for anyone who has it: the file's name and size (GET), or the file itself (download/). Nothing else about the organization is shown; a link that does not work is a plain 404. |

## system

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/system/backups/` | GET | `BackupListView` |  |
| `/api/v1/system/backups/run/` | POST | `BackupRunView` |  |
| `/api/v1/system/health/` | GET | `HealthView` | Health history and alerts for this installation (Super Administrator only). |
| `/api/v1/system/version/` | GET | `VersionView` | The installed IntraForge version (the repo-root VERSION file, as the portable export records it), for the web app's footer and welcome tour. Signed-in callers only: an anonymous caller is never told the version. |
| `/healthz` | GET | `HealthzView` | Liveness: process is up and can respond. No dependency checks — used by the container runtime/orchestrator to know whether to restart the process, not whether it's ready to serve real traffic. |
| `/metrics` | GET | `MetricsView` | Prometheus exposition format (Phase 11; docs/architecture/ROADMAP.md). Exposes dependency-up gauges computed at scrape time from the same checks /readyz runs. Deliberately does not expose request-count/ latency histograms — those need a registry shared across  |
| `/readyz` | GET | `ReadyzView` | Readiness: checks the dependencies a request would actually need (control-plane DB, tenant DB connection, Valkey) before the process is considered ready to receive traffic (docs/architecture/ARCHITECTURE.md Section 9). |

## workspaces

| Path | Methods | View | What it does |
|---|---|---|---|
| `/api/v1/organizations/<uuid:organization_id>/workspaces/` | GET, POST | `WorkspaceListCreateView` |  |
| `/api/v1/projects/<uuid:project_id>/` | GET | `ProjectDetailView` |  |
| `/api/v1/workspaces/<uuid:workspace_id>/` | GET | `WorkspaceDetailView` |  |
| `/api/v1/workspaces/<uuid:workspace_id>/projects/` | GET, POST | `ProjectListCreateView` |  |

