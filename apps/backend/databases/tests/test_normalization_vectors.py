"""One part-number normalization rule, proven identical in every place it runs.

The rule (databases/normalization.py): uppercase; remove whitespace -- exactly JavaScript's
`\s` -- and the ASCII hyphen-minus; keep everything else. The browser mirrors it (for ranking
only) and the separate spare-parts reference application uses the same rule, so the same
vectors are run by the frontend test suite (apps/frontend/src/lib/business.test.ts). Any change
to the rule must change tests/fixtures/part-number-normalization.json, which fails all three.
"""

import json
from pathlib import Path

from django.db import connection
from django.test import SimpleTestCase, TestCase

from catalogue_storage.models import normalize_part_number
from databases.normalization import SEPARATOR_CLASS, normalize_search_key


def _load_vectors():
    here = Path(__file__).resolve()
    candidates = [Path("/repo-tests/fixtures/part-number-normalization.json")]
    candidates += [
        parent / "tests" / "fixtures" / "part-number-normalization.json" for parent in here.parents
    ]
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))["vectors"]
    raise FileNotFoundError("tests/fixtures/part-number-normalization.json not found")


VECTORS = _load_vectors()


class PythonRuleTests(SimpleTestCase):
    def test_every_shared_vector(self):
        for vector in VECTORS:
            with self.subTest(vector["why"]):
                self.assertEqual(normalize_search_key(vector["input"]), vector["key"])

    def test_catalogue_storage_uses_the_identical_rule(self):
        for vector in VECTORS:
            with self.subTest(vector["why"]):
                self.assertEqual(normalize_part_number(vector["input"]), vector["key"])


class PostgresExpressionTests(TestCase):
    """The SQL side of search uses upper(regexp_replace(col, SEPARATOR_CLASS, '', 'g')) -- run the
    very same expression in PostgreSQL over every vector."""

    def test_the_sql_expression_agrees_with_every_vector(self):
        with connection.cursor() as cursor:
            for vector in VECTORS:
                cursor.execute(
                    "SELECT upper(regexp_replace(%s, %s, '', 'g'))", [vector["input"], SEPARATOR_CLASS]
                )
                with self.subTest(vector["why"]):
                    self.assertEqual(cursor.fetchone()[0], vector["key"])
