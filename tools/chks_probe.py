"""Probe the `CHKS` trailer that follows `LRSC` in `levels`-style records.

`script.rpf` records carry six chunks; records extracted from `levels.rpf` carry a
seventh, `CHKS`, whose payload is 12 bytes.  The first four bytes are a
**big-endian total record size** and match the decompressed body length in every
record measured.  The next four bytes are an unknown tag — not joaat32, not
crc32, not adler32, over the body, over the body prefix, or (tested here) over
the compressed stream.  The trailing `7a 70 70 70` is `0x70` memset filler.

    python3 tools/chks_probe.py --archive /path/levels.rpf --index output/index/levels.tsv
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import script_meta as sm


def joaat(data, seed=0):
    value = seed & 0xFFFFFFFF
    for byte in data:
        value = (value + byte) & 0xFFFFFFFF
        value = (value + (value << 10)) & 0xFFFFFFFF
        value ^= value >> 6
    value = (value + (value << 3)) & 0xFFFFFFFF
    value ^= value >> 11
    value = (value + (value << 15)) & 0xFFFFFFFF
    return value & 0xFFFFFFFF


def fnv1a(data):
    value = 0x811C9DC5
    for byte in data:
        value = ((value ^ byte) * 0x01000193) & 0xFFFFFFFF
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()

    sm.MAGICS[b"CHKS"] = "CHKS"
    import csv
    ranges = sorted((int(row["start"], 16), int(row["end"], 16))
                    for row in csv.DictReader(args.index.open(), delimiter="\t")
                    if row["kind"] == "zlib")

    counters = {"records": 0, "with_chks": 0, "size_matches": 0,
                "crc_body": 0, "crc_prefix": 0, "crc_compressed": 0,
                "joaat_body": 0, "joaat_compressed": 0, "fnv_body": 0}
    samples = []

    with args.archive.open("rb") as handle:
        for position, (start, end) in enumerate(ranges):
            handle.seek(start)
            raw = handle.read(end - start)
            try:
                body = zlib.decompress(raw)
            except zlib.error:
                continue
            if not body.startswith(b"PSIN"):
                continue
            if len(body) == 65536 and position + 1 < len(ranges):
                try:
                    nstart, nend = ranges[position + 1]
                    handle.seek(nstart)
                    body += zlib.decompress(handle.read(nend - nstart))
                except zlib.error:
                    pass
            counters["records"] += 1
            chunks = sm.walk(body)
            if not chunks or chunks[-1]["magic"] != "CHKS":
                continue
            counters["with_chks"] += 1
            offset = chunks[-1]["offset"]
            payload = body[offset + 8:offset + 8 + chunks[-1]["next"] - 8]
            if len(payload) < 8:
                continue
            size_be = struct.unpack_from(">I", payload, 0)[0]
            tag = payload[4:8]
            prefix = body[:offset]
            counters["size_matches"] += size_be == len(body)
            candidates = {
                "crc_body": zlib.crc32(body) & 0xFFFFFFFF,
                "crc_prefix": zlib.crc32(prefix) & 0xFFFFFFFF,
                "crc_compressed": zlib.crc32(raw) & 0xFFFFFFFF,
                "joaat_body": joaat(body),
                "joaat_compressed": joaat(raw),
                "fnv_body": fnv1a(body),
            }
            for name, value in candidates.items():
                if struct.pack("<I", value) == tag or struct.pack(">I", value) == tag:
                    counters[name] += 1
            if len(samples) < 5:
                samples.append((position, len(body), len(raw), payload.hex(),
                                {k: hex(v) for k, v in candidates.items()}))
            if counters["with_chks"] >= args.limit:
                break

    for position, length, compressed, payload, candidates in samples:
        print(f"record {position}: body {length} compressed {compressed} chks {payload}")
        print(f"   {candidates}")
    print()
    for name, value in counters.items():
        print(f"{name:16s} {value}")


if __name__ == "__main__":
    raise SystemExit(main())
