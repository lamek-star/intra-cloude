import uuid
from typing import ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("User must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        # "Superuser" here only means "a User record exists" — it grants no
        # platform privilege by itself. Platform-wide (Super Administrator)
        # access is a RoleAssignment with organization=None, assigned
        # separately (see permissions.services.grant_platform_role and the
        # `bootstrap_super_administrator` management command). Authorization
        # is never derived from a flag on User (ADR-0008).
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Platform-wide account lock, independent of any organization Membership status.",
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    # MFA (TOTP, Phase 10 — docs/architecture/ROADMAP.md). `mfa_secret_encrypted`
    # is set as soon as enrollment starts (`accounts/services.py:start_mfa_enrollment`)
    # but `mfa_enabled` only flips True once the user proves they can
    # actually generate a valid code (`confirm_mfa_enrollment`) — never
    # enabled from possession of the secret alone.
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret_encrypted = models.BinaryField(null=True, blank=True)
    mfa_confirmed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self):
        return self.first_name or self.email
