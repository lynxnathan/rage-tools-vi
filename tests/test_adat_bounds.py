"""ADAT extent-bound regressions, using generated in-memory headers only.

    python3 tests/test_adat_bounds.py
"""

import io
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from adat_index import MAX_BANK, MAX_STREAMS, bank_extent, extent_bank


class RecordingReader(io.BytesIO):
    def __init__(self, blob):
        super().__init__(blob)
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


def bank(flags, extent=0x1000, count=1, fallback=False):
    if flags == 0xFF21 and not fallback:
        table_at = 0x50
    elif flags == 0xFF02 and not fallback:
        table_at = 0x10 + 4 * count
    else:
        table_at = 0x10
    header_size = table_at + 8
    blob = bytearray(header_size)
    blob[:4] = b"ADAT"
    struct.pack_into("<HHII", blob, 4, 1, flags, count, header_size)
    struct.pack_into("<Q", blob, table_at,
                     (0x55 << 56) | (1 << 28) | (extent - 1))
    return bytes(blob)


class AdatBoundsTests(unittest.TestCase):
    def test_all_table_paths_honor_extent_limit(self):
        for flags, fallback in ((0xFF21, False), (0xFF02, False),
                                (0xFF21, True), (0xFF02, True),
                                (0xFF25, False), (0xFF61, False)):
            with self.subTest(flags=hex(flags), fallback=fallback):
                end, count, error = extent_bank(
                    io.BytesIO(bank(flags, extent=0x1800, fallback=fallback)),
                    0, limit=0x1000)
                self.assertIsNone(end)
                self.assertEqual(count, 1)
                self.assertIsNotNone(error)

    def test_extent_at_limit_is_accepted_at_nonzero_offset(self):
        for flags, fallback in ((0xFF21, False), (0xFF02, False),
                                (0xFF21, True), (0xFF02, True),
                                (0xFF25, False), (0xFF61, False)):
            with self.subTest(flags=hex(flags), fallback=fallback):
                prefix = b"\0" * 0x80
                end, count, error = extent_bank(
                    io.BytesIO(prefix + bank(flags, fallback=fallback)),
                    len(prefix), limit=0x1000)
                self.assertEqual((end, count, error), (0x1080, 1, None))

    def test_limit_does_not_select_a_shorter_table_suffix(self):
        for flags in (0xFF21, 0xFF02, 0xFF25, 0xFF61):
            with self.subTest(flags=hex(flags)):
                # The first of two valid records reaches beyond the caller's limit.
                # Reject the bank instead of dropping it to accept the final record.
                blob = bytearray(bank(flags, extent=0x1800, fallback=True))
                blob.extend(struct.pack("<Q", (0x55 << 56) | (1 << 28) | 0xFFF))
                struct.pack_into("<I", blob, 12, len(blob))
                end, count, error = extent_bank(io.BytesIO(blob), 0, limit=0x1000)
                self.assertIsNone(end)
                self.assertIsNotNone(error)

    def test_invalid_scanned_stream_counts_are_rejected(self):
        for flags in (0xFF25, 0xFF61):
            for count in (0, MAX_STREAMS + 1):
                with self.subTest(flags=hex(flags), count=count):
                    reader = RecordingReader(bank(flags, count=count))
                    end, actual_count, error = extent_bank(reader, 0)
                    self.assertIsNone(end)
                    self.assertEqual(actual_count, count)
                    self.assertEqual(error, "implausible stream count")
                    self.assertEqual(reader.read_sizes, [16])

    def test_oversized_headers_are_rejected_before_reading_them(self):
        for flags in (0xFF21, 0xFF02, 0xFF25, 0xFF61):
            for header_size, limit in ((MAX_BANK + 1, MAX_BANK), (0x2000, 0x1000)):
                with self.subTest(flags=hex(flags), header_size=header_size):
                    blob = bytearray(bank(flags))
                    struct.pack_into("<I", blob, 12, header_size)
                    reader = RecordingReader(blob)
                    end, count, error = extent_bank(reader, 0, limit=limit)
                    self.assertIsNone(end)
                    self.assertIsNotNone(error)
                    self.assertEqual(reader.read_sizes, [16])

    def test_legacy_count_is_checked_before_info_table_read(self):
        for count in (0, MAX_STREAMS + 1, 0xFFFFFFFF):
            with self.subTest(count=count):
                blob = b"ADAT" + struct.pack("<III", 0, count, 16)
                reader = RecordingReader(blob)
                end, actual_count, tags, flags, error = bank_extent(reader, 0)
                self.assertIsNone(end)
                self.assertEqual(actual_count, count)
                self.assertEqual(error, "implausible stream count")
                self.assertEqual(reader.read_sizes, [16])

    def test_legacy_valid_stream_counts_still_parse(self):
        for count in (1, MAX_STREAMS):
            with self.subTest(count=count):
                header_size = 16 + 4 * count + 8 * count
                blob = b"ADAT" + struct.pack("<III", 0, count, header_size)
                blob += struct.pack("<I", 1 << 29) * count
                record = (0x55 << 56) | (1 << 28) | header_size
                blob += struct.pack("<Q", record) * count
                end, actual_count, tags, flags, error = bank_extent(io.BytesIO(blob), 0)
                expected_end = (header_size + 1 + 0x7FF) // 0x800 * 0x800
                self.assertEqual((end, actual_count, tags, error),
                                 (expected_end, count, count, None))


if __name__ == "__main__":
    unittest.main()
