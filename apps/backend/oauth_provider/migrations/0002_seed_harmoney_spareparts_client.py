"""
Seeds the development OAuthClient registration for the Harmoney Spare
Parts project (docs/SPARE_PARTS_AUTH_INTEGRATION.md) as a real, reviewable,
version-controlled migration rather than an ad-hoc admin-API call against
a live deployment — this is dev/local-environment setup data, not a
production tenant record, and doing it this way means a fresh `docker
compose up` on any machine gets a working client with no manual step.

The plaintext secret is generated once, here, and printed to migration
output (captured in `docker compose logs`/migrate output) — never stored.
If this migration is ever re-run against a database where the client
already exists (idempotent by client_id), no new secret is issued and
nothing is printed; see the client's row in oauth-clients/ (admin API) or
rotate its secret there instead of re-running this migration.
"""

from django.db import migrations

DEV_CLIENT_ID = "ifc_harmoney_spareparts_dev"


def seed_client(apps, schema_editor):
    OAuthClient = apps.get_model("oauth_provider", "OAuthClient")
    if OAuthClient.objects.filter(client_id=DEV_CLIENT_ID).exists():
        return

    # Local import -- migrations should not import app code that itself
    # imports models at module scope in a way that could drift from the
    # historical migration graph; oauth_provider.crypto has no model
    # imports, so this is safe (same pattern permissions/migrations uses
    # for its own seed step elsewhere in this codebase).
    from oauth_provider.crypto import generate_token, hash_token

    secret = generate_token(32)
    OAuthClient.objects.create(
        name="Harmoney Spare Parts (development)",
        client_id=DEV_CLIENT_ID,
        client_secret_hash=hash_token(secret),
        application_type="confidential_web",
        redirect_uris=[
            "http://localhost:3000/auth/callback",
            "http://127.0.0.1:3000/auth/callback",
        ],
        post_logout_redirect_uris=[
            "http://localhost:3000/",
            "http://127.0.0.1:3000/",
        ],
        allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        enabled=True,
    )
    print(  # noqa: T201 -- deliberate one-time dev-secret handoff, see module docstring
        "\n"
        "==================================================================\n"
        "  Harmoney Spare Parts (development) OAuth client seeded.\n"
        f"  client_id:     {DEV_CLIENT_ID}\n"
        f"  client_secret: {secret}\n"
        "  (shown once -- copy it into the spare-parts app's own env now.)\n"
        "==================================================================\n"
    )


def remove_client(apps, schema_editor):
    OAuthClient = apps.get_model("oauth_provider", "OAuthClient")
    OAuthClient.objects.filter(client_id=DEV_CLIENT_ID).delete()


class Migration(migrations.Migration):
    dependencies = [("oauth_provider", "0001_initial")]
    operations = [migrations.RunPython(seed_client, remove_client)]
