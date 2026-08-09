"""
Thin, provider-agnostic wrapper around boto3's S3 client — MinIO locally,
AWS S3 or another S3-compatible provider later purely via configuration
(ADR-0004). Nothing outside this module should import boto3 directly.
"""

import re

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings

_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"\x1f\x8b", "application/gzip"),
]


def sniff_mime_type(head: bytes) -> str:
    """Minimal content-based MIME sniffing from a file's first bytes —
    the browser-supplied Content-Type is never trusted on its own
    (Section 8 of the master prompt). Covers common binary formats; falls
    back to text/plain for valid UTF-8, else application/octet-stream.
    Swap in a fuller library (e.g. python-magic) if broader coverage is
    needed later — not added now per Section 24 (avoid dependencies
    before they're needed)."""
    for signature, mime_type in _MAGIC_SIGNATURES:
        if head.startswith(signature):
            return mime_type
    try:
        head.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        return "application/octet-stream"


_UNSAFE_DISPOSITION_CHARS = re.compile(r'[\r\n"]')


def safe_content_disposition(filename: str) -> str:
    """Strips characters that could break out of the quoted-string header
    value or inject additional headers (CRLF injection) — `filename` is
    user-supplied (docs/architecture/DATA_MODEL.md: original_filename is
    untrusted, display-only)."""
    cleaned = _UNSAFE_DISPOSITION_CHARS.sub("", filename) or "download"
    return f'attachment; filename="{cleaned}"'


class ObjectStorageClient:
    def __init__(self):
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.OBJECT_STORAGE_ENDPOINT or None,
            aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_KEY,
            region_name=settings.OBJECT_STORAGE_REGION,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        self._bucket = settings.OBJECT_STORAGE_BUCKET_PREFIX

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def put_stream(self, key: str, fileobj, content_type: str) -> None:
        """Streams `fileobj` to S3 in chunks (boto3's `upload_fileobj`
        handles multipart upload internally) — never reads the whole file
        into memory (ROADMAP.md Phase 3 exit criteria)."""
        self._client.upload_fileobj(fileobj, self._bucket, key, ExtraArgs={"ContentType": content_type})

    def get_stream(self, key: str):
        """Returns a botocore `StreamingBody` for chunked reading."""
        return self._client.get_object(Bucket=self._bucket, Key=key)["Body"]

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def presigned_download_url(self, key: str, filename: str, expires_in: int = 300) -> str:
        """Not used as the default download path yet — see
        storage/views.py FileDownloadView — because the internal Docker
        DNS name in OBJECT_STORAGE_ENDPOINT isn't reachable from a
        browser outside the Docker network in this deployment topology.
        Kept as a real, working capability for when it is (real AWS S3,
        or a proxied MinIO endpoint) and for Phase 9 external sharing."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ResponseContentDisposition": safe_content_disposition(filename),
            },
            ExpiresIn=expires_in,
        )


_client: ObjectStorageClient | None = None


def get_client() -> ObjectStorageClient:
    global _client
    if _client is None:
        _client = ObjectStorageClient()
        _client.ensure_bucket()
    return _client
