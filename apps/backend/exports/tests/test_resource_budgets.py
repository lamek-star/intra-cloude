"""Reject hostile resource requests before decompression or key derivation."""

import io
import json
import zipfile
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from exports import container, restorer
from exports.restorer import PackageValidationError


def encrypted_header(**overrides):
    encryption = {
        "algorithm": "AES-256-GCM", "kdf": "argon2id",
        "kdf_params": {"time_cost": 3, "memory_cost_kib": 262144, "parallelism": 4},
        "salt": "00" * 16, "nonce": "00" * 12,
    }
    encryption.update(overrides)
    data = json.dumps({"format": "intracloud-portable-container", "encryption": encryption}).encode()
    return container.MAGIC + len(data).to_bytes(4, "big") + data + b"ciphertext"


class ResourceBudgetTests(SimpleTestCase):
    def test_hostile_kdf_cost_is_rejected_before_allocating_memory(self):
        data = encrypted_header(kdf_params={"time_cost": 999999, "memory_cost_kib": 2**40, "parallelism": 4})
        with patch("exports.container.hash_secret_raw") as derive:
            with self.assertRaises(container.ContainerError):
                container.read_container_payload(data, passphrase="demo")
        derive.assert_not_called()

    def test_wrong_header_shape_is_a_validation_error(self):
        for header in (b"[]", b"null", b"123", b"\xff"):
            with self.subTest(header=header), self.assertRaises(container.ContainerError):
                container.read_container_payload(container.MAGIC + len(header).to_bytes(4, "big") + header)

    def test_unknown_algorithm_is_rejected_before_derivation(self):
        with patch("exports.container.hash_secret_raw") as derive:
            with self.assertRaises(container.ContainerError):
                container.read_container_payload(encrypted_header(algorithm="unknown"), passphrase="demo")
        derive.assert_not_called()

    @override_settings(PORTABLE_MAX_EXPANDED_BYTES=128)
    def test_expansion_budget_is_checked_before_reading_manifest(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", b" " * 4096)
        with patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("decompression attempted")):
            with self.assertRaises(PackageValidationError):
                restorer.open_package(container.write_container(output.getvalue()))

    @override_settings(PORTABLE_MAX_MEMBERS=2)
    def test_member_count_budget_precedes_manifest_read(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            for number in range(3):
                archive.writestr(str(number), b"")
        with patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("read attempted")):
            with self.assertRaises(PackageValidationError):
                restorer.open_package(container.write_container(output.getvalue()))
