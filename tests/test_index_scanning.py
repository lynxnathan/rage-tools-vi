"""Chunk-boundary regressions for archive indexers, using synthetic bytes only.

    python3 tests/test_index_scanning.py
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import adat_index
import bink_index


class IndexScanningTests(unittest.TestCase):
    def scan(self, module, signature, offsets, chunk_size, limit=0):
        blob = bytearray(max(offsets, default=0) + len(signature) + chunk_size)
        for offset in offsets:
            blob[offset:offset + len(signature)] = signature
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.dat"
            path.write_bytes(blob)
            scanner = (module.find_banks if module is adat_index
                       else module.find_candidates)
            with patch.object(module, "CHUNK", chunk_size):
                return scanner(path, limit=limit)

    def test_signatures_at_read_boundary_are_unique(self):
        for module, signature in ((adat_index, b"ADAT"), (bink_index, b"KB2")):
            with self.subTest(indexer=module.__name__):
                self.assertEqual(self.scan(module, signature, [12, 24], 16),
                                 [12, 24])

    def test_limit_counts_distinct_candidates(self):
        for module, signature in ((adat_index, b"ADAT"), (bink_index, b"KB2")):
            with self.subTest(indexer=module.__name__):
                self.assertEqual(self.scan(module, signature, [12, 24, 40], 16,
                                           limit=2), [12, 24])

    def test_signatures_split_across_reads_are_found(self):
        for module, signature in ((adat_index, b"ADAT"), (bink_index, b"KB2")):
            for chunk_size in (1, 2, 3, 5, 7):
                with self.subTest(indexer=module.__name__, chunk=chunk_size):
                    self.assertEqual(self.scan(module, signature, [4, 12],
                                               chunk_size), [4, 12])

    def test_unaligned_signatures_are_ignored(self):
        for module, signature in ((adat_index, b"ADAT"), (bink_index, b"KB2")):
            with self.subTest(indexer=module.__name__):
                self.assertEqual(self.scan(module, signature, [3, 12], 7), [12])

    def test_empty_input_has_no_candidates(self):
        for module in (adat_index, bink_index):
            with self.subTest(indexer=module.__name__):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "empty.dat"
                    path.write_bytes(b"")
                    scanner = (module.find_banks if module is adat_index
                               else module.find_candidates)
                    self.assertEqual(scanner(path), [])

    def test_adat_scan_respects_requested_range(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.dat"
            path.write_bytes(b"ADAT" * 12)
            with patch.object(adat_index, "CHUNK", 16):
                self.assertEqual(adat_index.find_banks(path, start=12, stop=36),
                                 [12, 16, 20, 24, 28, 32])


if __name__ == "__main__":
    unittest.main()
