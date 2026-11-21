"""Resolve RPF9 pack extents from zero padding, with the declared count as oracle.

Every header observed so far is preceded by a zero-padding run, so a pack's end
is `next_header - padding_before_next_header`.  That boundary is exact whenever
the next header is a sibling.  When it is a child instead, the pack still owes
entries, so the count decides: a pack closes only once its direct items
(struct-root streams plus child packs) reach its declared N.

Struct roots are found by decoding streams, so this tool is meant to run on a
local archive copy, not the read-only volume during an extraction.
"""

import argparse
import bisect
import csv
import mmap
import struct
import zlib
from collections import Counter
from pathlib import Path

SELF_TAG = 5
TAG_MAX = 0x0A
MIN_HITS = 2


def align16(value):
    return (value + 15) // 16 * 16


def load_packs(census, archive):
    return sorted((int(row["offset"], 16), int(row["count"]), int(row["front_end"]),
                   int(row["trailer"]))
                  for row in csv.DictReader(census.open(), delimiter="\t")
                  if row["archive"] == archive)


def is_struct(body):
    for base in (0, 0x100):
        if base + 0x40 > len(body):
            continue
        hits = 0
        for offset in range(base, base + 0x40, 4):
            value = struct.unpack_from("<I", body, offset)[0]
            tag = value >> 28
            if not (SELF_TAG <= tag <= TAG_MAX) or value & 0xF:
                continue
            target = value & 0x0FFFFFFF
            if tag == SELF_TAG and not (base <= target < len(body)):
                continue
            hits += 1
        if hits >= MIN_HITS:
            return True
    return False


def padding_before(mm, offset, maximum=1 << 20):
    run = 0
    position = offset - 1
    while position >= 0 and run < maximum and mm[position] == 0:
        run += 1
        position -= 1
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--census", type=Path, default=Path("handoff/header-census-full.tsv"))
    parser.add_argument("--tsv", type=Path, default=None)
    args = parser.parse_args()

    packs = load_packs(args.census, args.archive.name)
    streams = sorted((int(row["start"], 16), int(row["end"], 16), int(row["decoded_bytes"] or 0))
                     for row in csv.DictReader(args.index.open(), delimiter="\t")
                     if row["kind"] == "zlib")
    stream_starts = [stream[0] for stream in streams]
    print(f"{args.archive.name}: packs {len(packs)}, streams {len(streams)}")

    with args.archive.open("rb") as handle:
        mm = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        size = len(mm)
        kinds = {}
        for index, stream in enumerate(streams):
            try:
                kinds[index] = is_struct(zlib.decompress(mm[stream[0]:stream[1]]))
            except zlib.error:
                kinds[index] = False

        events = [(row[0], 0, pack_index) for pack_index, row in enumerate(packs)]
        events.extend((stream[0], 1, index) for index, stream in enumerate(streams))
        events.sort()

        stack = []
        resolved = {}

        def close(pack, boundary):
            # The zero-padding boundary is exact for the last sibling only; for
            # every other pack the end follows its own last item or child.
            own = align16(pack["last_end"]) + pack["trailer"]
            end = min(max(own, pack["front_end_abs"] + pack["trailer"]), boundary)
            pack["end"] = end
            resolved[pack["offset"]] = pack
            if stack_parent := pack.get("parent"):
                stack_parent["last_end"] = max(stack_parent["last_end"], end)

        next_offset = None
        for event_index, (offset, kind, index) in enumerate(events):
            if kind == 0:
                next_offset = events[event_index + 1][0] if event_index + 1 < len(events) else size
                # Leaf fast path: if the pack's own window (up to the physical
                # boundary of the next header) already holds exactly N struct
                # roots, it is a leaf and closes on the physical boundary.  The
                # count is used only to *classify* leaf vs parent, never to
                # drive the walk, so an ambiguous N cannot collapse the tree.
                row = packs[index]
                front = row[0] + row[2]
                boundary = next_offset - padding_before(mm, next_offset) if next_offset else size
                lo = bisect.bisect_left(stream_starts, front)
                hi = bisect.bisect_left(stream_starts, boundary)
                own = sum(1 for k in range(lo, hi) if kinds.get(k))
                if own == row[1] and boundary > front:
                    leaf = {
                        "offset": row[0], "count": row[1], "trailer": row[3],
                        "front_end_abs": front, "items": own, "children": 0,
                        "direct": own, "last_end": boundary - row[3],
                    }
                    leaf["end"] = boundary
                    resolved[row[0]] = leaf
                    if stack:
                        stack[-1]["children"] += 1
                        stack[-1]["direct"] += 1
                        stack[-1]["last_end"] = max(stack[-1]["last_end"], boundary)
                    next_offset = events[event_index + 1][0] if event_index + 1 < len(events) else size
                    continue
                # Only a header can end a pack: trailing data streams after the
                # last counting entry still belong to it and must not close it.
                while stack:
                    top = stack[-1]
                    saturated = top["direct"] >= top["count"]
                    if saturated and offset >= top["front_end_abs"]:
                        boundary = offset - padding_before(mm, offset)
                        close(top, boundary)
                        stack.pop()
                    else:
                        break
                pack_offset, count, front_end, trailer = packs[index]
                pack = {
                    "offset": pack_offset,
                    "count": count,
                    "trailer": trailer,
                    "front_end_abs": pack_offset + front_end,
                    "items": 0,
                    "children": 0,
                    "direct": 0,
                    "last_end": pack_offset + front_end,
                }
                if stack:
                    stack[-1]["children"] += 1
                    stack[-1]["direct"] += 1
                    pack["parent"] = stack[-1]
                stack.append(pack)
            else:
                if not stack:
                    continue
                pack = stack[-1]
                if kinds.get(index):
                    pack["items"] += 1
                    pack["direct"] += 1
                pack["last_end"] = max(pack["last_end"], streams[index][1])

        for pack in reversed(stack):
            close(pack, size)
        mm.close()

    rows = []
    for offset in sorted(resolved):
        pack = resolved[offset]
        end = pack["end"]
        ok = pack["direct"] == pack["count"]
        rows.append((offset, pack["count"], pack["items"], pack["children"],
                     pack["direct"], end, end - pack["front_end_abs"], int(ok)))
    exact = sum(row[7] for row in rows)
    print(f"  packs resolved: {len(rows)}, count satisfied: {exact} ({exact / len(rows):.1%})")
    residuals = Counter(row[1] - row[4] for row in rows)
    print(f"  residual (N - direct): {residuals.most_common(6)}")
    aligned = sum(1 for row in rows if row[5] % 16 == 0)
    print(f"  ends 16-aligned: {aligned}/{len(rows)}")
    print(f"\n{'pack':>12} {'N':>4} {'structs':>7} {'children':>8} {'direct':>6} "
          f"{'end':>12} {'payload':>10}")
    for row in rows:
        print(f"0x{row[0]:010x} {row[1]:>4} {row[2]:>7} {row[3]:>8} {row[4]:>6} "
              f"0x{row[5]:010x} {row[6]:>10}")

    if args.tsv:
        args.tsv.parent.mkdir(parents=True, exist_ok=True)
        with args.tsv.open("w") as out:
            out.write("archive\toffset\tcount\tstructs\tchildren\tdirect\tend\tpayload\tok\n")
            for row in rows:
                out.write(f"{args.archive.name}\t0x{row[0]:x}\t{row[1]}\t{row[2]}\t{row[3]}\t"
                          f"{row[4]}\t0x{row[5]:x}\t{row[6]}\t{row[7]}\n")
        print(f"wrote {args.tsv}")


if __name__ == "__main__":
    main()
