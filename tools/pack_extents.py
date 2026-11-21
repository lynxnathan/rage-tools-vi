"""Resolve RPF9 pack extents from zero padding, in index-only mode.

Two signals, no payload decoding:

* **Zero padding.** Every header after the root is preceded by a contiguous
  zero run, so the pack immediately before a header ends at
  `header - padding`.  That boundary is exact for the last sibling.
* **Chains and the declared count.** A 64 KiB chain is the entry unit: a stream
  continues its predecessor when the predecessor decoded exactly 65,536 bytes
  and this stream starts on the align16 boundary of its end.  A header event
  closes every saturated pack under it; a pack is saturated when its direct
  items (chains plus child packs) reach its declared N, or when it holds no
  chains at all (a pure directory pack).

Because chains come from the index, this runs on the read-only volume while an
extraction is busy.
"""

import argparse
import bisect
import csv
from collections import Counter
from pathlib import Path

CHUNK = 65536


def align16(value):
    return (value + 15) // 16 * 16


def load_packs(census, archive):
    return sorted((int(row["offset"], 16), int(row["count"]), int(row["front_end"]),
                   int(row["trailer"]))
                  for row in csv.DictReader(census.open(), delimiter="\t")
                  if row["archive"] == archive)


def load_streams(index):
    return sorted((int(row["start"], 16), int(row["end"], 16), int(row["decoded_bytes"] or 0))
                  for row in csv.DictReader(index.open(), delimiter="\t")
                  if row["kind"] == "zlib")


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
    parser.add_argument("--unit", choices=("chains", "structs"), default="chains",
                        help="entry unit: 64 KiB chains (index only) or decoded "
                             "struct roots (needs the payload)")
    args = parser.parse_args()

    packs = load_packs(args.census, args.archive.name)
    streams = load_streams(args.index)
    starts = [stream[0] for stream in streams]

    if args.unit == "structs":
        # Struct mode decodes each stream; use it on a local archive copy.
        import mmap as _mmap
        import struct as _struct
        import zlib as _zlib

        def is_struct(body):
            for base in (0, 0x100):
                if base + 0x40 > len(body):
                    continue
                hits = 0
                for offset in range(base, base + 0x40, 4):
                    value = _struct.unpack_from("<I", body, offset)[0]
                    tag = value >> 28
                    if not (5 <= tag <= 0x0A) or value & 0xF:
                        continue
                    target = value & 0x0FFFFFFF
                    if tag == 5 and not (base <= target < len(body)):
                        continue
                    hits += 1
                if hits >= 2:
                    return True
            return False

        with args.archive.open("rb") as handle:
            mm = _mmap.mmap(handle.fileno(), 0, access=_mmap.ACCESS_READ)
            chain_of = []
            for stream in streams:
                try:
                    chain_of.append(0 if is_struct(_zlib.decompress(mm[stream[0]:stream[1]])) else -1)
                except _zlib.error:
                    chain_of.append(-1)
            mm.close()
        # Struct mode: each struct is its own item; non-structs are ignored.
        chain_of = [index if value == 0 else -1 - index
                    for index, value in enumerate(chain_of)]
        chain_starts = [stream[0] for stream, value in zip(streams, chain_of) if value >= 0]
    # Chain grouping, index only.
    if args.unit == "chains":
        chain_of = []
        chain_starts = []
        previous = None
        for stream in streams:
            continues = (previous is not None and previous[0] == CHUNK
                         and stream[0] == align16(previous[1]))
            if not continues:
                chain_starts.append(stream[0])
            chain_of.append(len(chain_starts) - 1)
            previous = (stream[2], stream[1])

    print(f"{args.archive.name}: packs {len(packs)}, streams {len(streams)}, "
          f"chains {len(chain_starts)}")

    with args.archive.open("rb") as handle:
        import mmap
        mm = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        size = len(mm)

        events = [(row[0], 0, index) for index, row in enumerate(packs)]
        events.extend((stream[0], 1, index) for index, stream in enumerate(streams))
        events.sort()
        header_bounds = [packs[index + 1][0] if index + 1 < len(packs) else size
                         for index in range(len(packs))]

        stack = []
        resolved = {}

        def close(pack, boundary):
            own = align16(pack["last_end"]) + pack["trailer"]
            end = min(max(own, pack["front_end_abs"] + pack["trailer"]), boundary)
            pack["end"] = end
            resolved[pack["offset"]] = pack
            parent = pack.get("parent")
            if parent is not None:
                parent["last_end"] = max(parent["last_end"], end)

        for position, (offset, kind, index) in enumerate(events):
            if kind == 0:
                boundary = header_bounds[index]
                low = bisect.bisect_left(starts, offset + packs[index][2])
                high = bisect.bisect_left(starts, boundary)
                window_chains = len({chain_of[k] for k in range(low, high) if chain_of[k] >= 0})
                while stack:
                    top = stack[-1]
                    saturated = top["direct"] >= top["count"]
                    if saturated:
                        close(top, offset - padding_before(mm, offset))
                        stack.pop()
                    else:
                        break
                pack = {
                    "offset": offset, "count": packs[index][1],
                    "trailer": packs[index][3],
                    "front_end_abs": offset + packs[index][2],
                    "items": 0, "children": 0, "direct": 0,
                    "last_end": offset + packs[index][2], "seen": set(),
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
                key = chain_of[index]
                if key < 0:
                    continue
                if key not in pack["seen"]:
                    pack["seen"].add(key)
                    pack["items"] += 1
                    pack["direct"] += 1
                pack["last_end"] = max(pack["last_end"], streams[index][1])

        for pack in reversed(stack):
            close(pack, size)
        mm.close()

    rows = []
    for offset in sorted(resolved):
        pack = resolved[offset]
        rows.append((offset, pack["count"], pack["items"], pack["children"],
                     pack["direct"], pack["end"], int(pack["direct"] == pack["count"])))
    exact = sum(row[6] for row in rows)
    print(f"  packs resolved: {len(rows)}, count satisfied: {exact} ({exact / len(rows):.1%})")
    print(f"  residual (N - direct): "
          f"{Counter(row[1] - row[4] for row in rows).most_common(6)}")
    print(f"  ends 16-aligned: {sum(1 for row in rows if row[5] % 16 == 0)}/{len(rows)}")
    print(f"\n{'pack':>12} {'N':>5} {'chains':>7} {'children':>8} {'direct':>6} {'end':>12}")
    for row in rows[:16]:
        print(f"0x{row[0]:010x} {row[1]:>5} {row[2]:>7} {row[3]:>8} {row[4]:>6} 0x{row[5]:010x}")

    if args.tsv:
        args.tsv.parent.mkdir(parents=True, exist_ok=True)
        with args.tsv.open("w") as out:
            out.write("archive\toffset\tcount\tchains\tchildren\tdirect\tend\tok\n")
            for row in rows:
                out.write(f"{args.archive.name}\t0x{row[0]:x}\t{row[1]}\t{row[2]}\t{row[3]}\t"
                          f"{row[4]}\t0x{row[5]:x}\t{row[6]}\n")
        print(f"wrote {args.tsv}")


if __name__ == "__main__":
    main()
