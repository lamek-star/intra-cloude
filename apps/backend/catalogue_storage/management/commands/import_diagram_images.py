"""
`python manage.py import_diagram_images --dir /path/to/drawings --license-confirmed`

Attaches locally held drawing files (`<figure key>.png`, e.g. `MA4481A.png`)
to catalogue Diagrams, so the spare-parts app can show them from this
platform's own object storage instead of leaning on the source website.

Refuses to do anything unless `--license-confirmed` is passed: like
`import_oem_catalogue`, storing image bytes is an explicit, separately
gated decision by an operator who has the right to use the files
(docs/CATALOGUE_STORAGE.md "Licensing"). Files are matched to a Diagram
by (provider, figure key = file name without extension); a Diagram that
does not exist yet is created empty, so the picture is already in place
when a part on that figure is imported later. A Diagram that is already
LOCALLY_STORED is left untouched. Duplicate file names (the same figure
saved from several pages) are attached once — first one found wins.
Anything that is not really a PNG/JPEG is skipped and reported.

`--dry-run` reports what would happen and writes nothing (no upload, no
rows).
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from storage.models import Bucket
from storage.services import UploadTooLarge, upload_file

from ...models import Diagram
from ...services import attach_local_image, ensure_catalogue_bucket

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


class _LocalFile:
    def __init__(self, path: Path):
        self.name = path.name
        self._handle = open(path, "rb")

    def read(self, size=-1):
        return self._handle.read(size)

    def seek(self, pos):
        return self._handle.seek(pos)

    def close(self):
        self._handle.close()


def looks_like_image(path: Path) -> bool:
    with open(path, "rb") as fh:
        head = fh.read(8)
    return head.startswith(PNG_MAGIC) or head.startswith(JPEG_MAGIC)


class Command(BaseCommand):
    help = "Attaches locally held figure drawings (<figure key>.png) to catalogue Diagrams."

    def add_arguments(self, parser):
        parser.add_argument("--dir", required=True, help="Directory (searched recursively) of drawing files.")
        parser.add_argument("--provider", default="toyota-epc")
        parser.add_argument("--bucket-id", default=None, help="Defaults to the catalogue drawings bucket.")
        parser.add_argument(
            "--license-confirmed",
            action="store_true",
            help="Confirms you may store and show these drawings. Nothing is imported without it.",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if not options["license_confirmed"]:
            raise CommandError(
                "Refusing to store drawings without --license-confirmed: pass it only if you have the "
                "right to store and show these files (see docs/CATALOGUE_STORAGE.md 'Licensing')."
            )
        root = Path(options["dir"])
        if not root.is_dir():
            raise CommandError(f"Not a directory: {root}")
        dry = options["dry_run"]
        provider = options["provider"]

        bucket = None
        if not dry:
            if options["bucket_id"]:
                try:
                    bucket = Bucket.objects.get(pk=options["bucket_id"])
                except Bucket.DoesNotExist as exc:
                    raise CommandError(f"No such bucket: {options['bucket_id']}") from exc
            else:
                try:
                    bucket = ensure_catalogue_bucket()
                except LookupError as exc:
                    raise CommandError(str(exc)) from exc

        stats = {"attached": 0, "already_stored": 0, "diagrams_created": 0, "duplicates": 0}
        skipped: list[str] = []
        seen: set[str] = set()
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            key = path.stem
            if key in seen:
                stats["duplicates"] += 1
                continue
            seen.add(key)
            if not looks_like_image(path):
                skipped.append(f"{path.name}: not a PNG/JPEG file")
                continue
            diagram = Diagram.objects.filter(provider=provider, provider_diagram_id=key).first()
            if diagram and diagram.license_status == Diagram.LicenseStatus.LOCALLY_STORED:
                stats["already_stored"] += 1
                continue
            if dry:
                stats["attached"] += 1
                stats["diagrams_created"] += 0 if diagram else 1
                continue
            local_file = _LocalFile(path)
            try:
                file_obj = upload_file(
                    bucket=bucket,
                    folder=None,
                    uploaded_file=local_file,
                    display_filename=path.name,
                    creator=bucket.created_by,
                )
            except UploadTooLarge as exc:
                skipped.append(f"{path.name}: {exc}")
                continue
            finally:
                local_file.close()
            with transaction.atomic():
                if diagram is None:
                    diagram = Diagram.objects.create(
                        provider=provider,
                        provider_diagram_id=key,
                        diagram_code=key,
                        license_status=Diagram.LicenseStatus.EXTERNAL_REFERENCE_ONLY,
                    )
                    stats["diagrams_created"] += 1
                attach_local_image(diagram=diagram, file_object=file_obj, actor=bucket.created_by)
            stats["attached"] += 1

        label = "DRY RUN — nothing was written" if dry else "Import complete"
        self.stdout.write(self.style.SUCCESS(f"{label}:"))
        self.stdout.write(f"  drawings attached:   {stats['attached']}")
        self.stdout.write(f"  already stored:      {stats['already_stored']}")
        self.stdout.write(f"  diagrams created:    {stats['diagrams_created']}")
        self.stdout.write(f"  duplicate file names: {stats['duplicates']}")
        if skipped:
            self.stdout.write(self.style.WARNING(f"  skipped: {len(skipped)}"))
            for line in skipped:
                self.stdout.write(f"    - {line}")
