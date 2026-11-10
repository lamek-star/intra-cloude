"""Movie Shop (ADR-0022): a catalogue of the shop's own video library. Only metadata lives here -- the films
stay on the shop's drives and the media agent (a Windows client of this API) reads and copies them; covers are
ordinary IntraForge files in the shop's ``movie-covers`` bucket."""

import uuid

from django.conf import settings
from django.db import models


class MovieShop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="movie_shops"
    )
    project = models.ForeignKey("workspaces.Project", on_delete=models.PROTECT, related_name="movie_shops")
    name = models.CharField(max_length=120)
    # Prices are in IntraForge Pay credits (whole credits; Pay keeps the money).
    default_price = models.PositiveIntegerField(default=40)
    # The media agent signs in as this application (ADR-0022 decision 3).
    agent_application = models.OneToOneField(
        "applications.Application", on_delete=models.PROTECT, related_name="movie_shop", null=True, blank=True
    )
    covers_bucket = models.OneToOneField(
        "storage.Bucket", on_delete=models.PROTECT, related_name="movie_shop", null=True, blank=True
    )
    # What the agent last reported: the PC's drives and their top folders (display data, re-validated on use).
    agent_report = models.JSONField(default=dict, blank=True)
    agent_seen_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movie_shops_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_movie_shop_name_per_org")
        ]

    def __str__(self) -> str:
        return self.name


class CategoryPrice(models.Model):
    """The price of every title in one category (folder), unless a title sets its own."""

    shop = models.ForeignKey(MovieShop, on_delete=models.CASCADE, related_name="category_prices")
    category = models.CharField(max_length=120)
    price = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["shop", "category"], name="unique_category_price")]

    def __str__(self) -> str:
        return f"{self.category}: {self.price}"


class Library(models.Model):
    """One folder on one of the shop PC's drives, as the media agent sees it (``D:\\Movies``)."""

    class Kind(models.TextChoices):
        FIXED = "fixed"
        REMOVABLE = "removable"
        NETWORK = "network"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(MovieShop, on_delete=models.CASCADE, related_name="libraries")
    name = models.CharField(max_length=120)
    path = models.CharField(max_length=260)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.FIXED)
    total_bytes = models.BigIntegerField(null=True, blank=True)
    free_bytes = models.BigIntegerField(null=True, blank=True)
    # A scan: the owner asks (scan_requested_at), the agent uploads titles tagged with the generation it
    # started, and finishing removes the titles that generation did not see. Readers see generation
    # `scanned_generation`.
    scan_requested_at = models.DateTimeField(null=True, blank=True)
    scan_generation = models.PositiveIntegerField(default=0)
    scanned_generation = models.PositiveIntegerField(default=0)
    last_scan_at = models.DateTimeField(null=True, blank=True)
    last_scan_message = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["shop", "path"], name="unique_library_path_per_shop")]

    def __str__(self) -> str:
        return self.name


class Title(models.Model):
    class Kind(models.TextChoices):
        MOVIE = "movie"
        SERIES = "series"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(MovieShop, on_delete=models.CASCADE, related_name="titles")
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="titles")
    # Where it is, relative to the library folder: "Action\\Desert Wind (2025).mp4" (backslashes, as on
    # Windows).
    relative_path = models.CharField(max_length=400)
    category = models.CharField(max_length=120)
    title = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.MOVIE)
    size_bytes = models.BigIntegerField(default=0)
    episodes = models.PositiveIntegerField(default=1)
    seen_generation = models.PositiveIntegerField(default=0)
    # The cover the agent uploaded, and the picture's fingerprint (size and time) so it is sent again only
    # when changed.
    cover = models.ForeignKey(
        "storage.FileObject", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    cover_fingerprint = models.CharField(max_length=64, blank=True)
    # The owner's own values: they survive every re-scan.
    price = models.PositiveIntegerField(null=True, blank=True)
    hidden = models.BooleanField(default=False)
    description = models.TextField(blank=True, max_length=2000)
    edited = models.BooleanField(default=False)  # the owner changed the title, year or category by hand
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "title"]
        constraints = [
            models.UniqueConstraint(fields=["library", "relative_path"], name="unique_title_path_per_library")
        ]
        indexes = [
            models.Index(fields=["shop", "category"]),
            models.Index(fields=["library", "seen_generation"]),
        ]

    def __str__(self) -> str:
        return self.title
