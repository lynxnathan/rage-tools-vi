"""Bulk extraction regressions using generated zlib streams only.

    python3 tests/test_bulk_extract_bounds.py
"""

import hashlib
import sys
import tempfile
import tracemalloc
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import bulk_extract


class BulkExtractBoundsTests(unittest.TestCase):
    def extract(self, payload, expected, outdir):
        packed = zlib.compress(payload)
        prefix = b"synthetic-prefix"
        with patch.object(bulk_extract, "MM", prefix + packed + b"suffix"):
            return bulk_extract.extract_one(
                (len(prefix), len(prefix) + len(packed), expected, outdir))

    def test_exact_decoded_length_writes_content_and_digest(self):
        payload = b"synthetic-content" * 50
        with tempfile.TemporaryDirectory() as tmp:
            result = self.extract(payload, len(payload), tmp)
            self.assertEqual(result[2], len(zlib.compress(payload)))
            self.assertEqual(result[3], len(payload))
            self.assertEqual(result[4], hashlib.sha256(payload).hexdigest())
            self.assertEqual(Path(result[5]).read_bytes(), payload)

    def test_zero_expected_length_preserves_unknown_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.extract(b"unknown length", 0, tmp)
            self.assertEqual(Path(result[5]).read_bytes(), b"unknown length")

    def test_smaller_and_larger_lengths_are_rejected_before_writing(self):
        for expected in (3, 40):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    self.extract(b"synthetic-content", expected, tmp)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_large_expansion_stays_bounded_by_indexed_length(self):
        packed = zlib.compress(b"x" * (8 << 20))
        with tempfile.TemporaryDirectory() as tmp, patch.object(bulk_extract, "MM", packed):
            tracemalloc.start()
            try:
                with self.assertRaises(ValueError):
                    bulk_extract.extract_one((0, len(packed), 16, tmp))
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertLess(peak, 512 << 10)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_truncated_stream_is_rejected_before_writing(self):
        payload = b"synthetic-content"
        packed = zlib.compress(payload)[:-1]
        with tempfile.TemporaryDirectory() as tmp, patch.object(bulk_extract, "MM", packed):
            with self.assertRaises((ValueError, zlib.error)):
                bulk_extract.extract_one((0, len(packed), len(payload), tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
