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


class Sale(models.Model):
    """A counter sale: titles for one customer, paid with IntraForge Pay (or cash), then copied by the media
    agent onto the customer's drive. Nothing here holds money: Pay keeps the payment and its receipt
    (ADR-0022 decision 6)."""

    class Status(models.TextChoices):
        AWAITING_PAYMENT = "awaiting_payment"
        PAID = "paid"  # paid; the agent is copying (or will)
        DONE = "done"  # every title copied
        CANCELLED = "cancelled"

    class Method(models.TextChoices):
        IFPAY = "ifpay"
        CASH = "cash"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(MovieShop, on_delete=models.CASCADE, related_name="sales")
    number = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AWAITING_PAYMENT)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.IFPAY)
    customer_name = models.CharField(max_length=120, blank=True)
    total = models.PositiveIntegerField()  # credits
    # Where the titles go: a drive the media agent reported ("E:\\"), into a folder named after the shop.
    destination = models.CharField(max_length=260)
    folder = models.CharField(max_length=120)
    pay_request_id = models.UUIDField(null=True, blank=True)
    pay_code = models.TextField(blank=True)  # what the wallet scans (the QR code carries it too)
    pay_qr_svg = models.TextField(blank=True)
    pay_expires_at = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=60, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movie_sales"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["shop", "status"])]

    def __str__(self) -> str:
        return self.number


class SaleLine(models.Model):
    """One title in a sale, as it was when sold (the catalogue may change later), and its copy onto the
    drive."""

    class Copy(models.TextChoices):
        WAITING = "waiting"
        COPYING = "copying"
        COPIED = "copied"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="lines")
    title = models.ForeignKey(Title, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    library = models.ForeignKey(Library, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    title_name = models.CharField(max_length=200)
    category = models.CharField(max_length=120)
    relative_path = models.CharField(max_length=400)
    kind = models.CharField(max_length=10)
    price = models.PositiveIntegerField()
    size_bytes = models.BigIntegerField(default=0)
    copy_status = models.CharField(max_length=10, choices=Copy.choices, default=Copy.WAITING)
    copied_bytes = models.BigIntegerField(default=0)
    copy_message = models.CharField(max_length=300, blank=True)
    copy_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["title_name"]

    def __str__(self) -> str:
        return self.title_name
