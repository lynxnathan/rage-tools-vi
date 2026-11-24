"""Index the `ADAT` containers inside an audio archive.

`audio.rpf` is 28.5 GB and the stream index classifies 99.93 % of it as
`unclassified`: the partitioner looks for zlib starts, and an AWC bank is neither
compressed nor self-describing at its start. The banks are still there, at 0x800
alignment, and each one declares its size through its tag table.

This walks them:

    ADAT header: magic, flags, count, header_size
    tables:      optional 0x400000 / 0x10000 / 0x200000 blocks, then `count` words
                 `id:29 | tag_count:3`   (the count is in the HIGH three bits)
    tag table:   sum(tag_count) records of 8 bytes
                 `type:8 | size:28 | offset:28`
    end          = max(offset + size over every tag), rounded up to 0x800

The last step is what makes the index possible: the bank's extent is the furthest
byte any of its tags reaches.

    python3 tools/adat_index.py /path/audio.rpf --out output/index/audio-adat.tsv
    python3 tools/adat_index.py /path/audio.rpf --limit 20 --show
"""

import argparse
import struct
import sys
from pathlib import Path

ALIGN = 0x800
CHUNK = 1 << 26
# Chunk/descriptor types seen in validated AWC banks. A random "ADAT" inside binary
# data produces arbitrary types, so this is the cheapest reliable filter.
KNOWN_TYPES = {0x55, 0x36, 0x76, 0xA3, 0xFA, 0x48, 0x5C, 0x68, 0x2B, 0x5A, 0xD9, 0xBD}
MAX_BANK = 256 << 20     # no validated bank is larger than this
MAX_STREAMS = 4096


def find_banks(path, limit=0):
    """Offsets of `ADAT` magics on the container alignment."""
    offsets = []
    with path.open("rb") as handle:
        position = 0
        carry = b""
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            data = carry + block
            start = 0
            while True:
                index = data.find(b"ADAT", start)
                if index < 0:
                    break
                absolute = position - len(carry) + index
                if absolute % ALIGN == 0:
                    offsets.append(absolute)
                    if limit and len(offsets) >= limit:
                        return offsets
                start = index + 1
            carry = data[-8:]
            position += len(block)
    return offsets


def bank_extent(handle, offset):
    """(end, count, total_tags, variant, error) for the bank at `offset`.

    A candidate is rejected unless its stream words and tag table are structurally
    plausible: counts in range, every tag type known, and every extent inside the
    largest observed bank. Random `ADAT` occurrences fail at the first check.
    """
    handle.seek(offset)
    head = handle.read(16)
    if len(head) < 16 or head[:4] != b"ADAT":
        return None, 0, 0, 0, "no magic"
    flags, count, header_size = struct.unpack_from("<III", head, 4)
    position = 16 + (4 if flags & 0x400000 else 0)
    if flags & 0x10000:
        position += count * 2
    if flags & 0x200000:
        position += (count + 1) * 4
    info = position
    position += count * 4
    handle.seek(info)
    words = handle.read(count * 4)
    if len(words) < count * 4:
        return None, count, 0, flags, "short info table"
    if count == 0 or count > MAX_STREAMS:
        return None, count, 0, flags, "implausible stream count"
    counts = [word >> 29 for word in struct.unpack(f"<{count}I", words)]
    if any(entry > 32 for entry in counts):
        return None, count, 0, flags, "implausible tag count"
    total_tags = sum(counts)
    handle.seek(position)
    table = handle.read(total_tags * 8)
    if len(table) < total_tags * 8:
        return None, count, total_tags, flags, "short tag table"
    end = 0
    for index in range(total_tags):
        (record,) = struct.unpack_from("<Q", table, index * 8)
        kind = record >> 56
        size = (record >> 28) & 0x0FFFFFFF
        tag_offset = record & 0x0FFFFFFF
        if kind not in KNOWN_TYPES:
            return None, count, total_tags, flags, "unknown tag type"
        end = max(end, tag_offset + size)
    if end == 0:
        return None, count, total_tags, flags, "no extents"
    if end > MAX_BANK:
        return None, count, total_tags, flags, "extent too large"
    end = offset + ((end + ALIGN - 1) // ALIGN) * ALIGN
    return end, count, total_tags, flags, None


def from_manifest(args, size):
    """Index banks from an extraction manifest: those extents were validated by decode."""
    import csv
    rows = []
    with args.manifest.open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            try:
                start, end = int(row["start"], 16), int(row["end"], 16)
            except (KeyError, ValueError):
                continue
            rows.append((start, end, row.get("flags", ""), row.get("streams", "")))
    rows.sort()
    total = sum(end - start for start, end, *_ in rows)
    gaps = 0
    previous = 0
    for start, end, *_ in rows:
        if start < previous:
            gaps += 1
        previous = max(previous, end)
    print(f"{len(rows):,} banks from {args.manifest.name}, {total:,} B "
          f"({total / size:.2%} of {size:,})")
    print(f"  out of order or overlapping: {gaps}")
    if rows and args.show:
        for start, end, flags, streams in rows[:5]:
            print(f"  bank +0x{start:x}..0x{end:x} ({end - start:,} B) "
                  f"flags {flags} streams {streams}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w") as handle:
            handle.write("kind\tstart\tend\tstored_bytes\tdecoded_bytes\tchain_start\n")
            # Same six columns as every other index. `chain_start` means "the range
            # this one continues", so it must stay empty here: writing the container
            # flags into it made the verifier (correctly) reject the file.
            for start, end, _flags, _streams in rows:
                handle.write(f"adat\t0x{start:x}\t0x{end:x}\t{end - start}\t\t\n")
        print(f"  wrote {args.out}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--limit", type=int, default=0, help="stop after N banks")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--manifest", type=Path,
                        help="use start/end from an extraction manifest instead of "
                             "parsing headers (the 0xff21 variant does not use the "
                             "tag-table layout this parser assumes)")
    args = parser.parse_args()

    if not args.archive.is_file():
        sys.exit(f"missing {args.archive}")
    size = args.archive.stat().st_size
    if args.manifest:
        return from_manifest(args, size)
    offsets = find_banks(args.archive, args.limit)
    print(f"{args.archive.name}: {size:,} B, {len(offsets):,} aligned ADAT banks")

    rows = []
    errors = {}
    total = 0
    previous_end = 0
    overlaps = 0
    with args.archive.open("rb") as handle:
        for offset in offsets:
            end, count, tags, flags, error = bank_extent(handle, offset)
            if error:
                errors[error] = errors.get(error, 0) + 1
                continue
            if offset < previous_end:
                overlaps += 1
                continue
            previous_end = end
            total += end - offset
            rows.append((offset, end, count, tags, flags))
            if args.show and len(rows) <= 5:
                print(f"  bank +0x{offset:x}..0x{end:x} ({end - offset:,} B) "
                      f"streams {count} tags {tags} flags 0x{flags:06x}")

    print(f"parsed {len(rows):,} banks, {total:,} B ({total / size:.2%} of the file)")
    if overlaps:
        print(f"  overlapping banks skipped: {overlaps}")
    if errors:
        print("  errors:", ", ".join(f"{k}={v}" for k, v in errors.items()))
    if rows:
        print(f"  largest bank: {max(r[1] - r[0] for r in rows):,} B")
        print(f"  streams total: {sum(r[2] for r in rows):,}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w") as handle:
            handle.write("kind\tstart\tend\tstored_bytes\tdecoded_bytes\tchain_start\n")
            for offset, end, count, tags, flags in rows:
                handle.write(f"adat\t0x{offset:x}\t0x{end:x}\t{end - offset}\t\t"
                             f"0x{flags:x}\n")
        print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
