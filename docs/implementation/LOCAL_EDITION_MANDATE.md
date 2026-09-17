# INTRAFORGE LOCAL EDITION v1.0
# CONTINUATION, PRODUCTIZATION, HARDENING & INVESTOR-DEMO MASTER PROMPT


======================================================================
ROLE
======================================================================

Act as the Principal Software Architect, Staff Backend Engineer,
Staff Frontend Engineer, Database Engineer, Security Engineer,
SRE, QA Lead, Release Engineer, Product Engineer, and technical
product owner responsible for finishing the EXISTING IntraForge
project.

You are not starting a new project.

You are continuing the existing IntraForge repository from its
CURRENT branch, CURRENT HEAD, CURRENT migrations, CURRENT tests,
CURRENT documentation, CURRENT deployment architecture, and all
previously completed implementation work.

Your responsibility is to transform the existing platform into:

    INTRAFORGE LOCAL EDITION v1.0

A trustworthy, fully functional, offline-first local business cloud
suitable for:

- spare-parts shops
- micro businesses
- small trading companies
- small offices
- local organizations
- small teams that want private local data storage and management

The immediate business objective is NOT to finish every possible
Enterprise capability.

The immediate objective is to produce a polished, reliable,
investor-demonstrable Local Edition that proves the architecture,
business usefulness, offline operation, data ownership, recovery,
and future Enterprise potential.


======================================================================
CONTINUATION REQUIREMENT — CRITICAL
======================================================================

THIS TASK IS A DIRECT CONTINUATION OF THE EXISTING INTRAFORGE PROJECT.

Do NOT:

- create a new repository
- initialize a replacement project
- fork IntraForge into a separate Local Edition codebase
- restart the roadmap
- redo completed App Platform phases
- replace the existing architecture without demonstrated necessity
- rewrite working functionality simply because another design looks cleaner
- remove Enterprise-capable foundations merely to simplify Local Edition

Work from the repository's actual current state.

Before changing anything, establish:

- repository path
- current branch
- current HEAD SHA
- working-tree status
- commits ahead/behind remote
- existing migrations
- current test status
- current deployment architecture
- current documentation state

Phases 1–10 and all existing implementations are the FOUNDATION of
this task.

"Local Edition" is a PRODUCTIZATION AND QUALIFICATION TARGET for
the existing system.

It is NOT:

- a rewrite
- a fork
- a second product codebase
- a simplified replacement architecture
- a new greenfield application

Preserve existing Enterprise-capable architecture internally.

Simplify the USER EXPERIENCE, not the architectural foundation.

If this prompt describes functionality that already exists:

    VERIFY IT.

If it works correctly:

    MARK IT VERIFIED AND MOVE ON.

Do NOT redo completed work merely because this prompt mentions it.


======================================================================
KNOWN PROJECT DIRECTION
======================================================================

The project has already progressed through the major App Platform
roadmap.

Treat existing completed work as authoritative only after verifying
it against code/tests/migrations.

Expected existing capabilities include substantial work around:

- Organizations
- Membership
- Organizational Units
- App Platform
- App Builder
- App Templates
- App Instances
- dynamic models
- fields
- relationships
- many-to-many relationships
- composite constraints
- runtime records
- attachments
- permissions
- ResourceGrants
- organizational-unit scoping
- Inventory & Sales
- management/reference templates
- workflows
- template upgrades
- external integrations
- OAuth/provider work
- webhooks
- catalogue storage
- Spare Parts integration work
- PostgreSQL
- object storage
- Valkey/Redis
- Celery
- audit
- export/restore
- backup/recovery
- Windows installer/appliance work
- Control Center
- LAN capability
- security qualification

Do not assume every item is complete merely because it appears here.

Verify reality.


======================================================================
PRODUCT VISION
======================================================================

IntraForge Local Edition v1.0 should be explainable to a customer
or investor in one sentence:

"IntraForge is a private local business cloud that lets small
businesses manage their files, products, inventory, sales,
purchasing and business data on infrastructure they control,
without depending on the public cloud."

The flagship demonstration will be a SPARE-PARTS BUSINESS.

However:

IntraForge must remain GENERIC.

The Spare Parts business is the reference application proving that
the generic platform works.

Do NOT turn the IntraForge core into a spare-parts-specific system.


======================================================================
LOCAL EDITION v1.0 PRODUCT PILLARS
======================================================================

Local Edition v1.0 should concentrate on five pillars:

1. LOCAL BUSINESS CLOUD

   Store business records and files locally.

2. BUSINESS APPLICATION PLATFORM

   Install and use editable business applications/templates.

3. SPARE PARTS / INVENTORY & SALES

   Provide a complete reference small-business workflow.

4. BACKUP AND RECOVERY

   Protect and restore the entire business.

5. FULL OFFLINE OPERATION

   Core functionality must not require internet access.

Everything implemented during this task must support one or more
of these pillars.


======================================================================
PRIMARY USER
======================================================================

Assume the primary Local Edition customer is NOT a software engineer.

Typical customer:

- spare-parts shop owner
- small warehouse
- general trader
- small retailer
- small company
- office administrator

They should not need to understand:

- Docker
- WSL
- PostgreSQL
- MinIO
- Valkey
- Celery
- Django
- Next.js
- migrations
- environment variables
- container networking
- terminal commands

These technologies may remain internally.

The product should expose INTRAFORGE concepts instead.


======================================================================
TARGET USER EXPERIENCE
======================================================================

The desired experience is approximately:

    Install IntraForge
            ↓
    Start IntraForge
            ↓
    Create Administrator
            ↓
    Create Organization
            ↓
    Choose Business Application
            ↓
    Start Working

Example first-run templates:

    Inventory & Sales
    Spare Parts
    Employee Management
    Documents
    Blank Application

Do not force users to configure infrastructure before performing
useful business work.


======================================================================
DEFINITION OF FUNCTIONALLY FINISHED
======================================================================

A non-technical small-business user should eventually be able to:

1. Install IntraForge on a clean supported Windows PC.

2. Start the local server/application.

3. Create the first administrator.

4. Create an organization/company.

5. Install the Spare Parts / Inventory & Sales application.

6. Create products.

7. Create multiple part numbers.

8. Search products by normalized part number.

9. Create suppliers.

10. Create customers.

11. Create warehouses.

12. Receive stock.

13. View stock per warehouse.

14. Record inventory movements correctly.

15. Create a sale/order using supported functionality.

16. Generate the supported invoice/sales document.

17. Deduct inventory correctly.

18. Upload product images.

19. Upload business documents.

20. Attach documents/files to appropriate business records.

21. Add additional users.

22. Assign appropriate permissions.

23. View audit/activity history.

24. Restart IntraForge.

25. Find all business data intact.

26. Restart Windows.

27. Find all business data intact.

28. Create a complete disaster-recovery backup.

29. Recover from that backup in a disposable clean environment.

30. Recover:

    - organization
    - application definitions
    - application instances
    - business records
    - inventory
    - transactions
    - files
    - images
    - required permissions/configuration

31. Perform the normal workflow with internet connectivity disabled.

If this complete journey works reliably, Local Edition has reached
the functional target.


======================================================================
FLAGSHIP INVESTOR DEMONSTRATION
======================================================================

Use a clearly labelled fictional/demo business such as:

    Harmoney Auto Parts LLC — DEMO

Example story:

Supplier
    ↓
Purchase / Goods Receiving
    ↓
Product
    ↓
Part Number
    ↓
Warehouse
    ↓
Inventory
    ↓
Stock Movement
    ↓
Customer
    ↓
Sale
    ↓
Invoice / Sales Document
    ↓
Updated Inventory

Example:

Receive:

    Toyota-compatible Demo Oil Filter
    Part Number: DEMO-90915-10009
    Quantity: 100

Result:

    Main Warehouse
    Available = 100

Then sell:

    Quantity = 5

Result:

    Stock Movement = -5
    Available = 95

The investor should be able to SEE that the system performs a
complete business operation.

Do not use unverified third-party OEM data as if it were verified.

Demo data must be explicitly identified as DEMO.


======================================================================
SCOPE FREEZE
======================================================================

FROM THIS POINT FORWARD:

Do NOT start another large feature phase merely because additional
features are possible.

Do NOT build speculative Enterprise functionality.

Do NOT add:

- AI features
- SaaS billing
- public marketplace
- multi-region clustering
- advanced enterprise accounting
- advanced payroll
- mobile applications
- dozens of new templates
- industry-specific government integrations
- unnecessary analytics platforms
- unrelated integrations

unless a small generic capability is genuinely required to satisfy
Local Edition acceptance criteria.

The operating principle is:

    FINISH
        ↓
    HARDEN
        ↓
    SIMPLIFY
        ↓
    QUALIFY
        ↓
    DEMONSTRATE

NOT:

    KEEP ADDING FEATURES


======================================================================
WORKING METHOD
======================================================================

Use evidence-driven development.

For every major area:

1. Inspect existing implementation.

2. Determine whether it is:

   COMPLETE
   PARTIAL
   MISSING
   BROKEN
   UNVERIFIED
   EXTERNALLY BLOCKED

3. Do not modify COMPLETE functionality unnecessarily.

4. Fix demonstrated problems.

5. Add regression coverage.

6. Run relevant qualification.

7. Document results.

8. Make a small logical local commit when appropriate.

9. Continue.

Do not create large speculative rewrites.


======================================================================
STEP 0 — ESTABLISH REPOSITORY TRUTH
======================================================================

Before implementation, inspect:

- current branch
- current HEAD
- working tree
- remote-tracking state
- recent commits
- migrations
- backend applications
- frontend
- App Platform
- App Builder
- templates
- runtime
- organizational units
- permissions
- ResourceGrants
- workflows
- upgrades
- Inventory & Sales
- Spare Parts integration
- catalogue storage
- OAuth/integration code
- webhooks
- storage/files
- backup/restore
- Windows installer
- Control Center
- WSL appliance
- Docker Compose
- security configuration
- CI
- SBOM
- vulnerability scanning
- test suites
- Playwright
- release documentation

Inspect at minimum the relevant documentation including:

- APP_PLATFORM_ROADMAP.md
- RELEASE_READINESS.md
- WINDOWS_QUALIFICATION_MATRIX.md
- TEST_STATUS.md
- AGENTS.md
- CLAUDE.md where relevant
- phase reports
- deployment documentation
- backup/restore documentation
- integration contracts
- security/threat-model documentation

Do not trust documentation blindly.

Compare documentation with implementation.

Create or update a CURRENT_STATE assessment.


======================================================================
STEP 1 — DOCUMENTATION RECONCILIATION
======================================================================

Reconcile project status documentation with reality.

Correct stale statements.

In particular verify whether documentation correctly represents:

- completion of App Platform phases
- upgrade UI
- webhooks UI
- management templates
- Inventory & Sales
- organizational units
- enterprise permissions
- workflow support
- template upgrades
- integration work
- catalogue storage
- OAuth/provider work
- current tests
- current release blockers

Do not claim functionality is qualified merely because it exists.

Maintain TWO distinct concepts:

    APPLICATION PLATFORM DEVELOPMENT READINESS

and:

    COMMERCIAL / WINDOWS RELEASE QUALIFICATION

These must not be conflated.


======================================================================
STEP 2 — FRESH CONSOLIDATED VERIFICATION
======================================================================

Run a fresh consolidated qualification from CURRENT HEAD.

Do not rely only on old phase reports.

Run the complete supported backend suite.

Use real infrastructure where tests require:

- PostgreSQL
- object storage
- Valkey/Redis
- Celery

Run appropriate:

- backend tests
- App Platform tests
- tenant-isolation tests
- authorization tests
- schema-evolution tests
- restore/recovery tests
- worker-crash tests
- migration checks
- ruff
- mypy

Frontend:

- TypeScript
- lint
- unit tests
- production build
- Playwright

Deployment:

- Docker builds
- Compose checks
- readiness checks

Record:

- exact commit SHA
- environment
- test counts
- skipped tests
- warnings
- flaky tests
- failures
- qualification limitations

Do NOT:

- hide failures
- delete failing tests
- weaken assertions
- repeatedly retry flaky tests until they happen to pass and call
  that qualification

Investigate failures.


======================================================================
STEP 3 — INVENTORY TRANSACTION CONSISTENCY
======================================================================

This is a high-priority business requirement.

Audit whether:

    StockMovement creation

and:

    Inventory quantity mutation

can succeed independently.

A state such as:

    StockMovement +50 committed

but:

    Inventory balance unchanged

must not silently occur.

Likewise:

    Inventory changed

without:

    corresponding movement/audit evidence

must not silently occur.

If this gap exists, implement the smallest appropriate GENERIC
transactional mechanism.

Desired behavior:

    BEGIN

        validate operation
        create StockMovement
        update Inventory
        write required audit data

    COMMIT

or:

    ROLLBACK EVERYTHING

Do not implement a frontend-only synchronization mechanism.

Do not create a fragile spare-parts-specific workaround if the
generic App Platform requires transactional actions.

Verify:

- goods receiving
- sales
- transfers
- adjustments
- insufficient stock
- duplicate submission
- concurrency
- transaction rollback
- failure between operations
- relevant process interruption

Inventory balances and movement history must remain consistent.


======================================================================
STEP 4 — PART × WAREHOUSE UNIQUENESS
======================================================================

Verify the previously identified Inventory uniqueness requirement.

A logical inventory position should not silently permit:

    Part A + Warehouse Dubai
    Part A + Warehouse Dubai

as independent stock positions where the model expects one balance.

Verify the generic relationship-column composite constraint
capability if already implemented.

Do not introduce an Inventory-specific uniqueness hack.

Concurrency must be protected by authoritative database-level
constraints where appropriate.


======================================================================
STEP 5 — LOCAL BUSINESS FILE CLOUD
======================================================================

Treat local file storage as a FIRST-CLASS PRODUCT FEATURE.

Verify the user experience for:

- uploading files
- downloading files
- browsing files
- deleting/managing files according to permissions
- attaching files to records
- product images
- supplier documents
- customer documents
- invoice documents
- contracts
- specifications

Example conceptual organization:

    Company Files
    │
    ├── Accounting
    ├── Customers
    ├── Suppliers
    ├── Products
    ├── Employees
    ├── Contracts
    ├── Invoices
    └── Other Documents

Do not expose MinIO terminology to ordinary users unless necessary.

Verify:

- persistence after restart
- tenant isolation
- authorization
- attachment authorization
- filenames
- unsafe path/object-key handling
- upload limits
- malicious/unsupported file handling according to existing policy
- backup inclusion
- restore correctness


======================================================================
STEP 6 — SPARE PARTS / INVENTORY & SALES FLAGSHIP
======================================================================

Use the existing generic App Platform.

Do NOT merge a standalone Spare Parts repository directly into
IntraForge core.

Preserve proper integration boundaries.

Verify the complete reference workflow:

    Supplier
        ↓
    Purchase / Receiving
        ↓
    Product
        ↓
    PartNumber
        ↓
    Warehouse
        ↓
    Inventory
        ↓
    StockMovement
        ↓
    Customer
        ↓
    Sales Order / supported sale
        ↓
    Invoice / supported sales document
        ↓
    Updated Inventory

Verify:

- product creation
- multiple part numbers
- normalized part-number search
- product images
- attachments
- supplier association
- customer association
- warehouse inventory
- receiving
- selling
- adjustments
- stock movement history
- invoice/sales document
- audit trail

Where vehicle compatibility is supported:

- verify many-to-many behavior
- verify tenant isolation
- verify editing
- verify search/display

Reference catalogue data must remain distinct from:

    COMPANY-OWNED PRODUCT DATA.

Do not bulk copy copyrighted third-party catalogues or images
without authorization.

Every imported/reference record should preserve provenance
according to the existing architecture.


======================================================================
STEP 7 — FIRST-RUN EXPERIENCE
======================================================================

Evaluate IntraForge as if you are a non-technical shop owner.

Target:

    Install
        ↓
    Open IntraForge
        ↓
    Create Administrator
        ↓
    Create Organization
        ↓
    Select Template
        ↓
    Start Working

The user should not need to manually:

- run Docker commands
- run migrations
- configure PostgreSQL
- configure object storage
- start Celery
- edit environment files
- configure internal networking

Audit and improve the experience without replacing the existing
deployment architecture unnecessarily.

Prefer:

    IntraForge Control Center

showing user-friendly concepts such as:

    Server: Running
    Database: Healthy
    File Storage: Healthy
    Backup Status
    Available Storage

and actions such as:

    Open IntraForge
    Backup
    Restore
    Start
    Stop

Infrastructure detail may be available under advanced diagnostics.


======================================================================
STEP 8 — PERMISSIONS USABILITY
======================================================================

The backend permission system may remain sophisticated.

The LOCAL user experience must be understandable.

Audit:

- users
- organization membership
- roles
- application access
- module/model grants
- action grants
- organizational-unit grants
- exact-unit scope
- descendant scope
- attachment access
- grant revocation

Where ordinary Local Edition administration still requires API/JSON
editing, determine whether a small UI is needed.

Do not build a giant Enterprise IAM console.

Use friendly organizational-unit selectors.

Use names in the UI while preserving stable IDs internally.

Server-side authorization remains authoritative.


======================================================================
STEP 9 — AUTHORIZATION ISOLATION
======================================================================

Audit all major read/write paths.

Unit/module/action scopes must not be enforced only on normal
record screens while alternative paths leak data.

Inspect:

- list
- retrieve
- create
- update
- delete
- search
- filters
- dashboards
- aggregates
- counts
- reports
- exports
- background jobs
- attachments
- external API
- bulk endpoints where present

Test:

- exact unit
- unit + descendants
- sibling denial
- parent/child boundaries
- cross-tenant denial
- module scope
- action scope
- record reassignment
- immediate grant revocation

Do not leak unauthorized information through:

- totals
- counts
- filenames
- export contents
- metadata
- job results
- error differences


======================================================================
STEP 10 — WORKFLOW UX
======================================================================

Do not build a new workflow engine if the existing one works.

Audit the existing workflow functionality.

Determine whether common Local Edition operations are blocked by
API/JSON-only configuration.

Where appropriate, provide only the minimum practical UI required
for demonstration/use.

Examples:

- pending approvals
- approval/rejection
- understandable status
- basic condition/action editing if necessary

Do not turn this into a new BPM product.


======================================================================
STEP 11 — WEBHOOK RELIABILITY INVESTIGATION
======================================================================

Investigate the reported reliability concern around webhook
delivery.

Specifically inspect failure windows such as:

    send HTTP
        ↓
    process crashes
        ↓
    delivered_at not persisted
        ↓
    retry
        ↓
    duplicate delivery

Also inspect:

    transaction commit
        ↓
    event creation
        ↓
    queue submission

Do not immediately rewrite the subsystem.

FIRST:

- understand current semantics
- write deterministic failure-injection tests
- reproduce actual behavior
- compare implementation with documentation

If duplicate delivery is possible:

Do NOT claim at-most-once.

Use accurate semantics.

If a generic reliability defect is demonstrated, fix it.

Prefer architecture based on:

    durable event identity
        ↓
    delivery attempt
        ↓
    HTTP request
        ↓
    durable delivery result
        ↓
    retry policy

Support receiver-side idempotency where appropriate.

Assess whether delivery history/replay is required for operational
safety.

Do not expand webhook functionality unnecessarily.


======================================================================
STEP 12 — EXTERNAL API RESILIENCE
======================================================================

Audit existing integration/API behavior.

Specifically investigate practical gaps already identified such as:

- record-create idempotency
- bulk record operations
- key rotation operations
- integration error handling

Only implement items that materially improve Local Edition
reliability or are required by existing functionality.

Do not expand this into a new Enterprise integration phase.


======================================================================
STEP 13 — BACKUP MODEL
======================================================================

This is RELEASE CRITICAL.

Clearly distinguish:

A. FULL APPLIANCE DISASTER-RECOVERY BACKUP

from:

B. PORTABLE `.icp` EXPORT/PACKAGE

Do not claim they are equivalent unless they genuinely are.

Audit `.icp`.

Document exactly what it includes and excludes.

Specifically determine whether it includes:

- organization
- AppTemplates
- AppInstances
- ModelDefinitions
- FieldDefinitions
- RelationshipDefinitions
- ConstraintDefinitions
- workflow definitions
- OrganizationalUnit references
- permissions
- records
- files
- template customization metadata

If `.icp` intentionally excludes App Platform metadata, document
that explicitly.

Do not automatically redesign `.icp` if full-appliance backup is
the intended Local Edition disaster-recovery mechanism.

But there must be ONE clearly supported method that can recover the
entire Local Edition business.


======================================================================
STEP 14 — FULL DISASTER-RECOVERY TEST
======================================================================

Perform the recovery test in a DISPOSABLE environment.

Do not destroy persistent development/reference data.

Test:

    initialize clean disposable environment

        ↓

    create organization

        ↓

    install business application

        ↓

    create products

        ↓

    create inventory

        ↓

    create business transaction

        ↓

    upload files/images

        ↓

    create users/permissions as appropriate

        ↓

    BACKUP

        ↓

    destroy disposable environment

        ↓

    fresh initialize/install

        ↓

    RESTORE

        ↓

    VERIFY

Verify important:

- record counts
- identifiers
- relationships
- inventory balances
- stock movements
- files
- file hashes where practical
- application definitions
- application instances
- permissions
- organizational units
- workflows
- required configuration

Document actual recovery behavior.

Do not claim disaster recovery based only on unit tests.


======================================================================
STEP 15 — OFFLINE QUALIFICATION
======================================================================

This is one of the defining Local Edition requirements.

Test with internet connectivity unavailable.

Normal business operations must continue.

Verify:

- login
- organization
- application opening
- App Runtime
- product CRUD
- part-number search
- inventory
- purchasing
- sales
- files
- images
- permissions
- workflows required by demo
- reports required by demo
- backup
- restore
- restart

Audit runtime dependencies.

No required:

- CDN
- remote font
- remote JavaScript
- cloud authentication
- external API
- telemetry endpoint
- package download

should prevent normal Local Edition operation.

Optional integrations may fail gracefully while offline.

Do not remove optional integration capabilities merely because
Local Edition is offline-first.


======================================================================
STEP 16 — RESTART / POWER-CYCLE RESILIENCE
======================================================================

Verify normal recovery after:

- browser close
- application restart
- backend restart
- worker restart
- container restart
- Windows restart where available

Business data must remain intact.

Services should return to a usable state without requiring a
developer to manually repair them.

Investigate obvious startup-order and readiness problems.


======================================================================
STEP 17 — BACKGROUND WORKER FAILURE
======================================================================

Preserve and extend existing worker-crash qualification where
necessary.

Verify important asynchronous operations under:

- worker restart
- worker child crash
- task redelivery
- duplicate execution
- process interruption

Do not assume previous restore-specific crash tests automatically
prove all current background workflows are safe.

Prioritize operations that affect business correctness.


======================================================================
STEP 18 — RESTORE OPERATIONAL GAPS
======================================================================

Review previously documented restore/recovery limitations.

Do not assume they were fixed unless code/tests prove it.

Investigate as appropriate:

- incomplete legacy restore jobs
- retention cleanup
- staging cleanup
- failed-job artifacts
- broker/outbox failure windows
- repeated worker crashes
- PostgreSQL outage
- object-storage outage
- Valkey outage
- network interruption
- observability
- operator recovery

Fix P0/P1 Local Edition reliability defects.

Document lower-priority limitations.


======================================================================
STEP 19 — SECURITY HARDENING
======================================================================

Review security from the perspective of a locally deployed
multi-user business application.

Verify:

- authentication
- MFA where supported
- session handling
- tenant isolation
- authorization
- unit scope
- module scope
- action scope
- IDOR/BOLA
- cross-tenant references
- file authorization
- import validation
- export authorization
- archive handling
- path traversal
- unsafe filenames
- SSRF
- connector safety
- credential handling
- secret storage
- CSRF
- CORS
- LAN configuration

Do not weaken security merely because the product runs locally.

A LAN user may still be untrusted.


======================================================================
STEP 20 — CONNECTOR DNS / SSRF REVIEW
======================================================================

Review previously identified connector address-resolution behavior.

If the architecture still:

    validates DNS/address
        ↓
    later connects using original hostname
        ↓
    performs another DNS lookup

investigate DNS rebinding exposure.

If unresolved and relevant to enabled Local Edition functionality,
fix using an appropriate generic safe-connect strategy.

Do not over-engineer disabled/unused connectors, but do not silently
leave an exposed high-impact path.


======================================================================
STEP 21 — ARCHIVE / IMPORT RESOURCE SAFETY
======================================================================

Verify import/restore/archive operations against:

- oversized archives
- expansion bombs
- malformed archives
- path traversal
- excessive file counts
- excessive memory
- excessive disk use
- malformed CSV
- CSV formula injection
- unsafe URLs
- malformed JSON/XML where supported

Implement practical Local Edition resource budgets where missing.

Do not attempt Enterprise-scale quotas unnecessarily.


======================================================================
STEP 22 — BROWSER E2E QUALIFICATION
======================================================================

Expand Playwright coverage around BUSINESS JOURNEYS.

Prioritize:

1. first-run organization creation

2. template installation

3. App Builder
   create → publish → install

4. product creation

5. part-number search

6. supplier creation

7. receiving inventory

8. inventory balance verification

9. customer creation

10. sale

11. stock deduction

12. file upload/download

13. permission assignment

14. permission revocation

15. organizational-unit scope

16. workflow execution

17. template upgrade

18. import where required

19. sharing where enabled

20. MFA where supported

Do not try to automate every visual detail.

Test critical business journeys.


======================================================================
STEP 23 — ACCESSIBILITY
======================================================================

Add practical automated accessibility scanning for critical
screens where feasible.

Check:

- keyboard navigation
- labels
- form errors
- focus behavior
- dialogs
- contrast where tooling can evaluate it
- semantic controls

Do not let accessibility work become an unlimited redesign.

Fix material issues in primary workflows.


======================================================================
STEP 24 — PERFORMANCE SANITY
======================================================================

This is NOT Enterprise-scale performance qualification.

Establish practical small-business baselines.

Use representative datasets such as:

- thousands of products
- multiple part numbers per product
- multiple warehouses
- thousands of stock movements
- customers
- suppliers
- invoices/orders
- documents/files

Measure representative:

- login
- dashboard
- product search
- normalized part-number search
- inventory list
- stock movement list
- record CRUD
- file browsing
- backup duration
- restore duration

Identify:

- N+1 queries
- missing indexes
- obvious sequential scans
- excessive memory
- pathological API behavior

Fix material problems.

Document:

- hardware
- dataset size
- test method
- observed results

Do not make unsupported scale claims.


======================================================================
STEP 25 — LOCAL EDITION UI POLISH
======================================================================

The application should feel like a PRODUCT.

Audit primary screens for:

- clear navigation
- consistent terminology
- empty states
- loading states
- errors
- success feedback
- confirmation dialogs
- destructive-action warnings
- responsive layout
- readable tables
- understandable forms
- search
- filtering

Do not perform a complete design-system rewrite.

Prioritize the investor-demo and small-business workflows.

Hide unnecessary infrastructure complexity.


======================================================================
STEP 26 — CONTROL CENTER
======================================================================

Review the existing Windows Control Center.

Target normal-user experience:

    IntraForge

    Server          Running
    Database        Healthy
    File Storage    Healthy
    Background Jobs Healthy

    Storage Available: ...

    [ Open IntraForge ]

    [ Backup ]
    [ Restore ]

    [ Start ]
    [ Stop ]

Advanced diagnostics may expose implementation detail.

Normal operation should not require PowerShell.


======================================================================
STEP 27 — INSTALLER EXPERIENCE
======================================================================

Audit the existing installer.

The target experience is:

    Setup.exe / MSI
        ↓
    Install
        ↓
    prerequisite handling
        ↓
    local appliance provisioning
        ↓
    launch Control Center
        ↓
    open IntraForge

Do not claim this is qualified until tested on the disposable
Windows qualification environment.

Preserve offline installation requirements.


======================================================================
STEP 28 — WSL2 PRODUCT POLICY
======================================================================

Do not silently choose a new WSL2 policy if the product decision
remains unresolved.

Document the alternatives clearly:

OPTION A

    IT/user enables required Windows/WSL2 prerequisites first.

OPTION B

    IntraForge installer enables required Windows features and
    provisions offline prerequisites.

For Local Edition investor demonstration, use the currently approved
path.

Do not make destructive host changes without authorization.


======================================================================
STEP 29 — WINDOWS QUALIFICATION
======================================================================

This is a SEPARATE release track.

Use:

    WINDOWS_QUALIFICATION_MATRIX.md

On a disposable clean Windows VM, eventually prove:

    fresh install
        ↓
    offline provisioning
        ↓
    first launch
        ↓
    organization creation
        ↓
    business app installation
        ↓
    business operations
        ↓
    restart
        ↓
    persistence
        ↓
    backup
        ↓
    restore
        ↓
    upgrade
        ↓
    repair if supported
        ↓
    uninstall
        ↓
    verify data-retention/removal policy

Test actual UAC/elevation behavior.

Test actual WSL import/provisioning.

If Windows ISO or another required input is unavailable:

MARK:

    EXTERNALLY BLOCKED

Do not fake evidence.


======================================================================
STEP 30 — LAN MODE
======================================================================

Single-computer Local Edition is first priority.

Then qualify LAN Server Mode.

Target:

    IntraForge Server PC
            │
            ├── Local browser
            │
            └── LAN
                 ↓
            Second Client
                 ↓
            Browser
                 ↓
            IntraForge

Verify:

- login
- business app
- CRUD
- inventory
- files
- logout
- authorization

A bridged VM may count as:

    BRIDGED-VM LAN VERIFIED

but not:

    PHYSICAL SECOND-MACHINE VERIFIED

unless actually tested on a separate physical machine.

Do not enable public internet exposure.


======================================================================
STEP 31 — VULNERABILITY POLICY
======================================================================

Review current vulnerability scanning.

If scans currently return success regardless of findings, define
a practical release policy.

For example, distinguish:

- informational
- low
- medium
- high
- critical

Use justified blocking criteria.

Do not blindly block on every scanner warning.

Do not blindly ignore every scanner warning.

Document accepted risks.


======================================================================
STEP 32 — LICENSE COMPLIANCE
======================================================================

Audit runtime/distributed dependencies.

Establish repeatable license-compliance evidence.

Identify:

- package
- version
- license
- distribution implications
- notices required

Generate/maintain third-party notices where appropriate.

Do not distribute dependencies without understanding their license.


======================================================================
STEP 33 — SBOM
======================================================================

Ensure release evidence covers the whole delivered appliance as
practically as possible.

Include:

- backend dependencies
- frontend dependencies
- container/appliance components
- rootfs/distributed system components where relevant

Prefer reproducible SBOM generation.

Attach/store SBOM as release evidence.

Do not claim full-appliance coverage if coverage is partial.


======================================================================
STEP 34 — SIGNING
======================================================================

Preserve existing signing mechanisms.

Do not claim the Windows release is signed unless verified using a
real signing certificate.

If no certificate is available:

    SIGNING — EXTERNALLY BLOCKED

Document the mechanism and remaining requirement.


======================================================================
STEP 35 — DEMO DATA
======================================================================

Create a reproducible DEMO dataset.

Suggested organization:

    Harmoney Auto Parts LLC — DEMO

Suggested data:

Warehouses:

    Main Warehouse
    Shop Floor

Suppliers:

    Demo Supplier A
    Demo Supplier B

Customers:

    Demo Retail Customer
    Demo Workshop Customer

Products:

    Demo Oil Filter
    Demo Air Filter
    Demo Brake Pad Set
    Demo Spark Plug
    Demo Drive Belt

Part numbers must be clearly fictional/demo unless verified.

Include:

- inventory
- stock movements
- supplier records
- customers
- example transaction
- documents
- images that are owned/generated/licensed for demonstration

Do not use copyrighted Nengun imagery without authorization.

Do not represent demo numbers as genuine OEM data.


======================================================================
STEP 36 — INVESTOR DEMO SCRIPT
======================================================================

Create:

    docs/INVESTOR_DEMO.md

Target length:

    approximately 10–15 minutes.

The demonstration should tell ONE STORY.

Suggested sequence:

1. Explain:

   "IntraForge is running entirely on this computer."

2. Demonstrate offline status where practical.

3. Open Control Center.

4. Show health.

5. Open IntraForge.

6. Open:

   Harmoney Auto Parts LLC — DEMO

7. Show dashboard.

8. Search a part number.

9. Open product.

10. Show image/document.

11. Show warehouse inventory.

12. Receive stock.

13. Show resulting stock movement.

14. Sell stock.

15. Show updated inventory.

16. Show invoice/sales document.

17. Upload/open a business document.

18. Briefly show users/permissions.

19. Briefly show audit trail.

20. Create/show backup.

21. Explain tested recovery.

22. Explain LAN Server Mode.

23. Finish by explaining Enterprise expansion.

Do not make claims unsupported by qualification evidence.


======================================================================
STEP 37 — ENTERPRISE INVESTMENT STORY
======================================================================

Do NOT implement these features now merely for the demo.

Document the future path.

Potential future Enterprise investment areas:

- centralized private-cloud deployment
- multi-server deployment
- high availability
- advanced disaster recovery
- enterprise SSO
- identity-provider integration
- advanced RBAC/policy
- larger organization hierarchy
- enterprise observability
- centralized fleet management
- managed updates
- advanced workflow automation
- integration ecosystem
- larger application/template ecosystem
- analytics
- enterprise APIs
- commercial support
- security certification work
- scalable deployment architecture

Show that Local Edition is the foundation.

Do not pretend future functionality already exists.


======================================================================
STEP 38 — PRODUCT DOCUMENTATION
======================================================================

Prepare/reconcile professional Local Edition documentation.

Include:

1. Product Overview
2. Local Edition Architecture
3. Offline Architecture
4. Installation
5. First Run
6. Control Center
7. Organization Setup
8. Users
9. Permissions
10. Organizational Units
11. Local File Storage
12. App Platform
13. App Builder
14. Templates
15. Spare Parts
16. Inventory
17. Purchasing
18. Sales
19. Part Numbers
20. Warehouses
21. Documents/Attachments
22. Audit
23. Backup
24. Restore
25. Offline Operation
26. LAN Mode
27. Security Model
28. Upgrade
29. Uninstall
30. Troubleshooting
31. Known Limitations
32. Qualification Status
33. Enterprise Roadmap
34. Investor Demo

For every major feature, distinguish where appropriate:

    IMPLEMENTED
    QUALIFIED
    PARTIALLY QUALIFIED
    EXPERIMENTAL
    DEFERRED
    EXTERNALLY BLOCKED


======================================================================
STEP 39 — PRESERVE REFERENCE ENVIRONMENTS
======================================================================

Preserve the existing:

    Phase 8 Reference Apps

organization and its installed reference applications unless
explicitly authorized to remove them.

Use it as regression evidence for:

- migrations
- template upgrades
- backward compatibility
- existing installations

Automated tests must NOT depend exclusively on this persistent
environment.

Tests must remain reproducible from clean state.


======================================================================
STEP 40 — TEMPLATE UPGRADE REGRESSION
======================================================================

Use existing reference applications to prove future migrations and
template upgrades do not unexpectedly destroy:

- customer records
- customer customization
- relationships
- constraints
- permissions
- workflows
- template state

Do not overwrite customer modifications silently.


======================================================================
STEP 41 — DATA OWNERSHIP PRINCIPLE
======================================================================

Local Edition's business value depends heavily on local ownership.

Verify the product behaves consistently with the principle:

    Customer controls the computer.
    Customer controls the storage.
    Customer controls the business data.
    Core operation does not depend on a public cloud account.

Do not make absolute legal/privacy claims.

Document actual architecture and behavior.


======================================================================
STEP 42 — NO FALSE COMPLETION
======================================================================

Do not call something:

    production ready
    commercially ready
    enterprise ready
    fully secure
    fully tested
    disaster-proof
    highly available

unless evidence supports that exact statement.

In particular:

ALL APP PLATFORM PHASES COMPLETE

does NOT mean:

COMMERCIAL RELEASE QUALIFIED.

Keep those concepts separate.


======================================================================
PRIORITY ORDER
======================================================================

Use this priority hierarchy unless repository evidence requires a
small adjustment.

P0 — MUST RESOLVE OR EXPLICITLY BLOCK

- data corruption
- inventory inconsistency
- cross-tenant security
- backup failure
- restore failure
- inability to operate offline
- installer cannot install target product
- destructive migration
- critical authentication/authorization bypass

P1 — SHOULD RESOLVE FOR LOCAL EDITION

- important permission usability
- attachment isolation
- major workflow usability
- webhook reliability defect in shipped functionality
- serious E2E gaps
- vulnerability policy
- license/release evidence
- important operational recovery gaps
- important performance defects

P2 — CAN FOLLOW INVESTOR DEMO IF DOCUMENTED

- broader accessibility polish
- advanced workflow UI
- webhook replay UX
- bulk APIs not needed by demo
- advanced admin UX
- lower-risk observability improvements

P3 — ENTERPRISE/FUTURE

- large-scale clustering
- HA
- advanced analytics
- advanced integrations
- multi-region
- advanced enterprise management
- speculative product expansion


======================================================================
INVESTOR DEMO READINESS VS COMMERCIAL READINESS
======================================================================

These are NOT the same.

It is acceptable for:

    INVESTOR DEMONSTRATION READINESS = READY

while:

    COMMERCIAL WINDOWS RELEASE QUALIFICATION = BLOCKED

if, for example:

- signing certificate is unavailable
- physical second LAN machine has not been tested
- final installer qualification is incomplete

The report must state this honestly.


======================================================================
GIT RULES
======================================================================

Do NOT:

- push
- merge
- tag
- rebase
- force push
- rewrite Git history
- delete persistent reference data
- remove important user data
- perform destructive Windows host changes

without explicit authorization.

Local commits are permitted when appropriate for the existing
workflow.

Prefer small logical commits.

For each major checkpoint:

    implementation
        ↓
    tests
        ↓
    documentation
        ↓
    local commit
        ↓
    next checkpoint


======================================================================
DESTRUCTIVE OPERATIONS
======================================================================

Any test requiring destruction of:

- current persistent organization
- development database
- persistent Docker volumes
- WSL distribution
- Windows installation
- host configuration
- user files

must use a disposable environment or require explicit authorization.

Do not destroy the developer's primary environment for a recovery
test.


======================================================================
EXTERNAL BLOCKERS
======================================================================

If progress requires something only the user can provide, mark it
explicitly.

Examples:

    WINDOWS ISO — EXTERNALLY BLOCKED

    CODE SIGNING CERTIFICATE — EXTERNALLY BLOCKED

    PHYSICAL SECOND LAN MACHINE — EXTERNALLY BLOCKED

    WSL2 PRODUCT POLICY — USER DECISION REQUIRED

Do not repeatedly stop the entire project because one external item
is unavailable.

Continue every independent task safely possible.


======================================================================
AUTONOMOUS EXECUTION
======================================================================

Do not interrupt the user after every minor implementation decision.

Use professional engineering judgment for:

- implementation detail
- refactoring required for correctness
- test structure
- documentation
- naming
- small UI corrections
- bug fixes

Ask the user only when a decision:

- changes product scope materially
- requires destructive action
- requires external credentials/certificate/hardware
- requires push/merge/tag
- has significant irreversible architectural consequences
- cannot reasonably be resolved from repository evidence

Otherwise continue.


======================================================================
STOP CONDITIONS
======================================================================

Stop a specific implementation path and report before proceeding if
you discover:

- risk of data loss
- fundamental architecture conflict
- destructive migration risk
- serious security regression
- licensing problem
- need to bypass third-party access controls
- need for unavailable secrets/certificates
- requirement to destroy non-disposable user data
- requirement to push/merge/tag without authorization

Do not hide these behind workarounds.


======================================================================
FINAL LOCAL EDITION ACCEPTANCE JOURNEY
======================================================================

The target end-to-end journey is:

    CLEAN COMPUTER
          ↓
    INSTALL INTRAFORGE
          ↓
    START
          ↓
    CREATE ADMIN
          ↓
    CREATE COMPANY
          ↓
    INSTALL SPARE PARTS / INVENTORY APP
          ↓
    CREATE SUPPLIER
          ↓
    CREATE PRODUCTS
          ↓
    CREATE PART NUMBERS
          ↓
    CREATE WAREHOUSE
          ↓
    RECEIVE INVENTORY
          ↓
    SEARCH PART NUMBER
          ↓
    VIEW STOCK
          ↓
    CREATE CUSTOMER
          ↓
    SELL PRODUCT
          ↓
    GENERATE SUPPORTED SALES DOCUMENT
          ↓
    VERIFY INVENTORY DEDUCTION
          ↓
    UPLOAD BUSINESS FILES
          ↓
    MANAGE USER ACCESS
          ↓
    VIEW AUDIT
          ↓
    RESTART SYSTEM
          ↓
    VERIFY PERSISTENCE
          ↓
    CREATE BACKUP
          ↓
    DESTROY DISPOSABLE TEST ENVIRONMENT
          ↓
    FRESH INITIALIZE
          ↓
    RESTORE
          ↓
    VERIFY BUSINESS RECOVERY
          ↓
    DISCONNECT INTERNET
          ↓
    VERIFY CORE BUSINESS OPERATION

This journey is more important than adding another platform phase.


======================================================================
FINAL QUALIFICATION REPORT
======================================================================

When all work safely possible in the current environment is
complete, create a professional:

    INTRAFORGE LOCAL EDITION v1.0
    FINAL QUALIFICATION REPORT

Include:

A. REPOSITORY STATE

- branch
- HEAD SHA
- clean/dirty status
- ahead/behind
- commits created during this work

B. ARCHITECTURE

- current architecture
- Local Edition deployment architecture
- major components
- data/storage architecture

C. EXISTING WORK VERIFIED

List previously completed features that were inspected and verified
without unnecessary rewriting.

D. CHANGES MADE

For every change:

- problem
- root cause
- implementation
- tests
- commit

E. BACKEND QUALIFICATION

Exact results.

F. FRONTEND QUALIFICATION

Exact results.

G. BROWSER QUALIFICATION

Exact Playwright/E2E results.

H. INVENTORY CONSISTENCY

Evidence.

I. DATABASE CONSTRAINTS

Evidence.

J. FILE STORAGE

Evidence.

K. PERMISSIONS

Evidence.

L. SECURITY

Findings and unresolved risks.

M. OFFLINE OPERATION

Evidence.

N. BACKUP

Evidence.

O. RESTORE

Evidence.

P. FAILURE RECOVERY

Worker/service interruption evidence.

Q. PERFORMANCE

Dataset/hardware/results.

R. WINDOWS

Exact qualification state.

S. LAN

Exact qualification state.

T. SIGNING

Exact state.

U. SBOM

Exact coverage.

V. LICENSE COMPLIANCE

Exact state.

W. VULNERABILITIES

Findings/accepted risks/blockers.

X. DOCUMENTATION

Documents created/updated.

Y. INVESTOR DEMO

Exact demo readiness and script.

Z. REMAINING ISSUES

Classify every remaining issue:

    P0
    P1
    P2
    P3
    EXTERNALLY BLOCKED


======================================================================
FINAL STATUS — MUST BE THREE SEPARATE VERDICTS
======================================================================

Do NOT provide one vague "ready/not ready" conclusion.

Provide exactly these three independent statuses:

--------------------------------------------------
1. LOCAL EDITION FUNCTIONAL READINESS
--------------------------------------------------

READY
or
READY WITH DOCUMENTED LIMITATIONS
or
NOT READY

Explain evidence.

--------------------------------------------------
2. INVESTOR DEMONSTRATION READINESS
--------------------------------------------------

READY
or
READY WITH DOCUMENTED LIMITATIONS
or
NOT READY

Explain whether the complete investor demonstration can be
performed reliably.

--------------------------------------------------
3. COMMERCIAL RELEASE QUALIFICATION
--------------------------------------------------

QUALIFIED
or
PARTIALLY QUALIFIED
or
NOT QUALIFIED
or
EXTERNALLY BLOCKED

Explain remaining Windows/signing/LAN/release requirements.


======================================================================
SUCCESS CRITERION
======================================================================

Do not optimize for:

    number of features
    number of phases
    number of files
    number of endpoints

Optimize for:

    COMPLETE BUSINESS JOURNEYS
    DATA CORRECTNESS
    LOCAL OWNERSHIP
    OFFLINE OPERATION
    RECOVERY
    SECURITY
    SIMPLICITY
    DEMONSTRABILITY


The final objective is:

A trustworthy, understandable, fully functional offline
small-business platform that demonstrates the IntraForge concept
today while preserving a credible technical foundation for future
Enterprise development.

The question that should guide every remaining engineering decision
is:

"Can I hand a Windows computer running IntraForge to a small
spare-parts shop or micro-business, have them actually use it
offline to manage their business and files, and reliably recover
their data if something goes wrong?"

If the answer is YES, with qualification evidence, IntraForge Local
Edition v1.0 has achieved its present objective.

Begin by establishing repository truth from CURRENT HEAD.

Do not restart the project.

Do not redo completed phases.

Continue from the existing implementation.