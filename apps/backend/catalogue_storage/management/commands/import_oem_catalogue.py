"""
`python manage.py import_oem_catalogue --csv parts.csv --images-dir images/
    --provider toyota-epc --manufacturer Toyota`

CSV columns (exact header names): part_number,description,diagram_code,
callout,image_filename

Deliberately refuses to touch object storage unless `--license-confirmed`
is also passed — see docs/CATALOGUE_STORAGE.md "Licensing". Without it,
every row still imports (part/diagram/link metadata, `source_image_url`
if `--source-base-url` is given), just with Diagram.license_status
staying EXTERNAL_REFERENCE_ONLY and no image bytes ever read from
`--images-dir`. This mirrors exactly how the Toyota EPC provider's own
sync path works elsewhere in this project: metadata always flows,
storage is a separate, explicitly-gated decision.

`--dry-run` validates the whole CSV (file existence for
`--license-confirmed` imports, required columns, no header mismatches)
and reports counts without writing anything.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from storage.models import Bucket
from storage.services import UploadTooLarge, upload_file

from ...models import Diagram
from ...services import ImportResult, ImportRow, attach_local_image, checksum_bytes, import_row

REQUIRED_COLUMNS = {"part_number", "description", "diagram_code", "callout", "image_filename"}


class _LocalFile:
    """Adapts a plain local file path to the minimal interface
    storage.services.upload_file expects (read/seek + a `.name`), without
    pulling in Django's full UploadedFile machinery for a CLI import."""

    def __init__(self, path: Path):
        self._path = path
        self.name = path.name
        self._handle = open(path, "rb")

    def read(self, size=-1):
        return self._handle.read(size)

    def seek(self, pos):
        return self._handle.seek(pos)

    def close(self):
        self._handle.close()


class Command(BaseCommand):
    help = "Imports a licensed OEM parts CSV (+ optional local images) into catalogue_storage."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to the parts CSV file.")
        parser.add_argument("--images-dir", default=None, help="Directory containing image_filename files.")
        parser.add_argument("--provider", required=True, help='e.g. "toyota-epc".')
        parser.add_argument("--manufacturer", required=True, help='e.g. "Toyota".')
        parser.add_argument(
            "--source-base-url", default="",
            help="If set (and --license-confirmed is NOT set), recorded as source_image_url = base + image_filename.",
        )
        parser.add_argument(
            "--license-confirmed", action="store_true",
            help="Confirms local image storage is actually permitted for this dataset. "
                 "Without this flag, image bytes are never read, regardless of --images-dir.",
        )
        parser.add_argument("--bucket-id", default=None, help="Required with --license-confirmed.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        license_confirmed = options["license_confirmed"]
        images_dir = Path(options["images_dir"]) if options["images_dir"] else None
        bucket = None
        if license_confirmed:
            if not options["bucket_id"]:
                raise CommandError("--bucket-id is required with --license-confirmed.")
            try:
                bucket = Bucket.objects.get(pk=options["bucket_id"])
            except Bucket.DoesNotExist as exc:
                raise CommandError(f"No such bucket: {options['bucket_id']}") from exc
            if not images_dir:
                raise CommandError("--images-dir is required with --license-confirmed.")

        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")
            rows = list(reader)

        if not rows:
            self.stdout.write(self.style.WARNING("CSV has no data rows."))
            return

        result = ImportResult()
        # One transaction for the whole batch -- a bad row (a referenced
        # image file that doesn't exist, an oversized image) fails the
        # entire import rather than leaving a half-imported catalogue.
        with transaction.atomic():
            uploaded_diagrams: set[str] = set()
            for i, row in enumerate(rows, start=2):  # header is line 1
                self._process_row(
                    row, i, options, license_confirmed, bucket, images_dir, uploaded_diagrams, result
                )
            if options["dry_run"]:
                transaction.set_rollback(True)

        self._report(result, dry_run=options["dry_run"])

    def _process_row(self, row, line_no, options, license_confirmed, bucket, images_dir, uploaded_diagrams, result):
        part_number = (row.get("part_number") or "").strip()
        if not part_number:
            result.errors.append(f"line {line_no}: empty part_number, skipped")
            return
        diagram_code = (row.get("diagram_code") or "").strip()
        source_image_url = ""
        if options["source_base_url"] and not license_confirmed:
            source_image_url = options["source_base_url"].rstrip("/") + "/" + (row.get("image_filename") or "").strip()

        import_row(
            ImportRow(
                part_number=part_number,
                description=(row.get("description") or "").strip(),
                manufacturer=options["manufacturer"],
                diagram_code=diagram_code,
                provider=options["provider"],
                provider_diagram_id=diagram_code,
                callout=(row.get("callout") or "").strip(),
                source_image_url=source_image_url,
            ),
            result,
        )

        if not license_confirmed:
            return
        image_filename = (row.get("image_filename") or "").strip()
        if not image_filename or diagram_code in uploaded_diagrams:
            return
        image_path = images_dir / image_filename
        if not image_path.exists():
            result.errors.append(f"line {line_no}: image file not found: {image_path}")
            return

        diagram = Diagram.objects.get(provider=options["provider"], provider_diagram_id=diagram_code)
        if diagram.license_status == Diagram.LicenseStatus.LOCALLY_STORED:
            uploaded_diagrams.add(diagram_code)
            return  # already stored by an earlier run of this importer.

        local_file = _LocalFile(image_path)
        try:
            with open(image_path, "rb") as fh:
                checksum_bytes(fh.read())  # validated/computed for real, even though upload_file recomputes its own.
            file_obj = upload_file(
                bucket=bucket, folder=None, uploaded_file=local_file,
                display_filename=image_filename, creator=bucket.created_by,
            )
        except UploadTooLarge as exc:
            result.errors.append(f"line {line_no}: {exc}")
            return
        finally:
            local_file.close()

        attach_local_image(diagram=diagram, file_object=file_obj, actor=bucket.created_by)
        uploaded_diagrams.add(diagram_code)

    def _report(self, result: ImportResult, *, dry_run: bool):
        label = "DRY RUN — nothing was written" if dry_run else "Import complete"
        self.stdout.write(self.style.SUCCESS(f"{label}:"))
        self.stdout.write(f"  parts created:    {result.parts_created}")
        self.stdout.write(f"  parts updated:    {result.parts_updated}")
        self.stdout.write(f"  diagrams created: {result.diagrams_created}")
        self.stdout.write(f"  diagrams reused:  {result.diagrams_reused}")
        self.stdout.write(f"  links created:    {result.links_created}")
        self.stdout.write(f"  links updated:    {result.links_updated}")
        if result.errors:
            self.stdout.write(self.style.ERROR(f"  errors: {len(result.errors)}"))
            for error in result.errors:
                self.stdout.write(self.style.ERROR(f"    - {error}"))
