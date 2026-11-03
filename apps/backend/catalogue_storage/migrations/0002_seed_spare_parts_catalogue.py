"""
Seeds this integration's bootstrap identity/organization/Application
credential (the "backend business data" access the spare-parts project
needs — distinct from oauth_provider's end-user SSO client) and one
real, verified sample OEMPart/Diagram/DiagramPart, exactly as the
"First end-to-end proof" this feature's own spec calls for: `15690-65010`
— Toyota "VALVE ASSY, OIL COOLER RELIEF", diagram MAB896 (catalog
EU/671450, section 1503 "ENGINE OIL COOLER"), callout `15690`, real
hotspot rect `{536,672}–{602,692}`. Every value below was read live from
the Toyota EPC aggregator during this feature's development, not
invented — see docs/CATALOGUE_STORAGE.md "First end-to-end proof".

`license_status` is EXTERNAL_REFERENCE_ONLY: redistribution permission
for toyota-epc images remains unverified (unchanged since
oauth_provider's own seed migration and every other Toyota-EPC-related
decision in this project) — only `source_image_url` + provenance is
recorded, no image bytes are stored.

A real, reviewable migration (not an ad-hoc admin-API call) for the same
reason oauth_provider's seed is one: reproducible on any fresh
`docker compose up`, no manual step, no live human session required.

Uses the REAL (not migration-frozen `apps.get_model`) User/Organization/
Application classes throughout: register_application/issue_credential
(applications/services.py) construct real model instances internally, and
Django refuses to assign a frozen-state instance to a real model's
ForeignKey (`"Application.organization" must be a "Organization"
instance`) — mixing the two only works when nothing crosses that
boundary. The Organization itself is created directly (not via
organizations.services.create_organization), which also assigns the
creator an "organization-administrator" RoleAssignment requiring the
permission catalog to already be seeded — a management command
(seed_permissions), never guaranteed to have run yet on a freshly
migrated database such as a test database. This app only needs an
Organization to own its Application on, nothing more.
"""

import uuid

from django.db import migrations


BOOTSTRAP_EMAIL = "catalogue-import@service.internal"
ORG_NAME = "Harmoney Spare Parts — Catalogue Ops"
APPLICATION_NAME = "Harmoney Spare Parts — Catalogue Storage"


def seed(apps, schema_editor):
    from accounts.models import User
    from applications.models import Application
    from applications.services import issue_credential, register_application
    from organizations.models import Organization

    OEMPart = apps.get_model("catalogue_storage", "OEMPart")
    Diagram = apps.get_model("catalogue_storage", "Diagram")
    DiagramPart = apps.get_model("catalogue_storage", "DiagramPart")

    if Application.objects.filter(name=APPLICATION_NAME).exists():
        return  # idempotent — see module docstring.

    bootstrap_user, _ = User.objects.get_or_create(
        email=BOOTSTRAP_EMAIL, defaults={"first_name": "Catalogue Import", "is_active": True}
    )
    bootstrap_user.set_unusable_password()
    bootstrap_user.save(update_fields=["password"])

    organization = Organization.objects.filter(name=ORG_NAME).first()
    if organization is None:
        organization = Organization.objects.create(
            id=uuid.uuid4(), name=ORG_NAME, slug="harmoney-spare-parts-catalogue-ops",
            created_by=bootstrap_user,
        )

    application = register_application(
        organization=organization,
        name=APPLICATION_NAME,
        description="Server-to-server bearer access for the spare-parts backend's OEM part/diagram search.",
        owner=bootstrap_user,
    )
    # `token` is already the full, formatted bearer credential
    # (TOKEN_PREFIX + credential id + "." + secret) -- see
    # applications/services.py:issue_credential's own return type.
    credential, token = issue_credential(service_account=application.service_account, actor=bootstrap_user)

    print(  # noqa: T201 -- deliberate one-time dev-secret handoff, see module docstring
        "\n"
        "==================================================================\n"
        "  Harmoney Spare Parts — Catalogue Storage credential seeded.\n"
        f"  organization:  {ORG_NAME}\n"
        f"  application:   {APPLICATION_NAME}\n"
        f"  bearer token:  {token}\n"
        "  (shown once -- copy it into the spare-parts app's own env now.)\n"
        "==================================================================\n"
    )

    part = OEMPart.objects.create(
        id=uuid.uuid4(),
        manufacturer="Toyota",
        part_number="15690-65010",
        normalized_part_number="1569065010",
        description="VALVE ASSY, OIL COOLER RELIEF",
    )
    diagram = Diagram.objects.create(
        id=uuid.uuid4(),
        provider="toyota-epc",
        provider_diagram_id="MAB896",
        diagram_code="MAB896",
        source_image_url="https://toyota-epc.aftermarketcatalog.com/image/figure/EU/A2/MAB896.png",
        license_status="EXTERNAL_REFERENCE_ONLY",
    )
    DiagramPart.objects.create(
        id=uuid.uuid4(),
        diagram=diagram,
        part=part,
        callout="15690",
        x=536,
        y=672,
        width=602 - 536,
        height=692 - 672,
    )


def unseed(apps, schema_editor):
    from applications.models import Application
    from organizations.models import Organization

    OEMPart = apps.get_model("catalogue_storage", "OEMPart")
    Application.objects.filter(name=APPLICATION_NAME).delete()
    Organization.objects.filter(name=ORG_NAME).delete()
    OEMPart.objects.filter(normalized_part_number="1569065010").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalogue_storage", "0001_initial"),
        ("applications", "0001_initial"),
        ("organizations", "0001_initial"),
    ]
    operations = [migrations.RunPython(seed, unseed)]
