from django.test import SimpleTestCase

from databases.models import DBColumn
from imports.inspect import InspectionError, detect_delimiter, detect_encoding, infer_type, inspect_sample


class DetectEncodingTests(SimpleTestCase):
    def test_plain_ascii_detected_as_utf8_variant(self):
        self.assertIn(detect_encoding(b"id,name\n1,alice\n"), ("utf-8-sig", "utf-8"))

    def test_utf8_bom_detected(self):
        content = b"\xef\xbb\xbfid,name\n1,alice\n"
        self.assertEqual(detect_encoding(content), "utf-8-sig")

    def test_invalid_utf8_falls_back_to_latin1(self):
        # 0xff is not valid UTF-8 on its own.
        content = b"id,name\n1,caf\xe9\n"
        self.assertEqual(detect_encoding(content), "latin-1")


class DetectDelimiterTests(SimpleTestCase):
    def test_comma(self):
        self.assertEqual(detect_delimiter("id,name,email\n1,alice,a@example.com\n"), ",")

    def test_semicolon(self):
        self.assertEqual(detect_delimiter("id;name;email\n1;alice;a@example.com\n"), ";")

    def test_tab(self):
        self.assertEqual(detect_delimiter("id\tname\n1\talice\n"), "\t")


class InferTypeTests(SimpleTestCase):
    def test_integers(self):
        self.assertEqual(infer_type(["1", "2", "-3"]), DBColumn.DataType.INTEGER)

    def test_decimals(self):
        self.assertEqual(infer_type(["1.5", "2.0", "-3.25"]), DBColumn.DataType.DECIMAL)

    def test_booleans(self):
        self.assertEqual(infer_type(["true", "false", "yes", "no"]), DBColumn.DataType.BOOLEAN)

    def test_dates(self):
        self.assertEqual(infer_type(["2026-01-01", "2026-12-31"]), DBColumn.DataType.DATE)

    def test_datetimes(self):
        self.assertEqual(
            infer_type(["2026-01-01T10:00:00", "2026-01-02T11:30:00"]), DBColumn.DataType.DATETIME
        )

    def test_mixed_values_fall_back_to_text(self):
        self.assertEqual(infer_type(["1", "abc", "true"]), DBColumn.DataType.TEXT)

    def test_all_empty_falls_back_to_text(self):
        self.assertEqual(infer_type(["", "", ""]), DBColumn.DataType.TEXT)

    def test_blank_values_are_ignored_when_inferring(self):
        self.assertEqual(infer_type(["1", "", "2"]), DBColumn.DataType.INTEGER)


class InspectSampleTests(SimpleTestCase):
    def test_full_preview_shape(self):
        content = b"id,name,active\n1,alice,true\n2,bob,false\n"
        result = inspect_sample(content)
        self.assertEqual(result["headers"], ["id", "name", "active"])
        self.assertEqual(len(result["sample_rows"]), 2)
        types = {c["csv_column"]: c["inferred_type"] for c in result["columns"]}
        self.assertEqual(types["id"], DBColumn.DataType.INTEGER)
        self.assertEqual(types["active"], DBColumn.DataType.BOOLEAN)

    def test_empty_file_raises(self):
        with self.assertRaises(InspectionError):
            inspect_sample(b"")
