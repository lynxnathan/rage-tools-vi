"""Build an entry-level manifest for `core_bvh4.rpf` from the payload model.

The archive's entries come in two shapes, both verified from payload evidence:

  pair*         a 208-byte descriptor stream followed by its data stream
  header_only*  a single small struct stream (160, 192, 240, 256, 272, ... bytes)

Descriptors pair with the immediately following stream (3,967/4,000 sampled),
and a pack's descriptor count equals its declared entry count in 1,070 of 1,282
packs.  Header-only entries are the unpaired streams in the packs that fall
short of the declared count.

Output rows carry the pack offset, entry index within the pack, shape, the two
stream ranges, and the decoded sizes.  `declared_ok` marks packs whose entry
count equals the header's N, so downstream users can filter to verified packs.
"""

import argparse
import bisect
import csv
from collections import Counter
from pathlib import Path

DESCRIPTOR = 208
HEADER_ONLY_MAX = 65536


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-name", default="core_bvh4.rpf")
    parser.add_argument("--census", type=Path, default=Path("handoff/header-census-full.tsv"))
    parser.add_argument("--index", type=Path, default=Path("output/index/core_bvh4.tsv"))
    parser.add_argument("--tsv", type=Path, default=Path("handoff/core-bvh4-entries.tsv"))
    args = parser.parse_args()

    packs = sorted((int(row["offset"], 16), int(row["count"]))
                   for row in csv.DictReader(args.census.open(), delimiter="\t")
                   if row["archive"] == args.archive_name)
    streams = sorted((int(row["start"], 16), int(row["end"], 16), int(row["decoded_bytes"] or 0))
                     for row in csv.DictReader(args.index.open(), delimiter="\t")
                     if row["kind"] == "zlib")
    starts = [row[0] for row in streams]
    print(f"packs {len(packs)}, streams {len(streams)}")

    rows = []
    verified_packs = 0
    stats = Counter()
    for position, (head, count) in enumerate(packs):
        end = packs[position + 1][0] if position + 1 < len(packs) else 1 << 62
        low = bisect.bisect_left(starts, head)
        high = bisect.bisect_left(starts, end)
        window = streams[low:high]
        entries = []
        used = set()
        at = 0
        while at < len(window):
            stream = window[at]
            if stream[2] == DESCRIPTOR and at + 1 < len(window):
                data = window[at + 1]
                entries.append(("pair", stream, data))
                used.update({at, at + 1})
                at += 2
            else:
                at += 1
        leftovers = [stream for index, stream in enumerate(window) if index not in used]
        for stream in leftovers:
            if stream[2] <= HEADER_ONLY_MAX:
                entries.append(("header_only", stream, None))
            else:
                entries.append(("unpaired_large", stream, None))
        entries.sort(key=lambda entry: entry[1][0])

        declared_ok = len(entries) == count
        verified_packs += declared_ok
        stats["packs"] += 1
        stats["declared_ok" if declared_ok else "declared_short"] += 1
        for index, (shape, first, second) in enumerate(entries):
            stats[shape] += 1
            rows.append({
                "pack": f"0x{head:x}",
                "entry": index,
                "shape": shape,
                "declared_count": count,
                "declared_ok": int(declared_ok),
                "stream": f"0x{first[0]:x}",
                "stored": first[1] - first[0],
                "decoded": first[2],
                "data": "" if second is None else f"0x{second[0]:x}",
                "data_stored": "" if second is None else second[1] - second[0],
                "data_decoded": "" if second is None else second[2],
            })

    fields = ["pack", "entry", "shape", "declared_count", "declared_ok", "stream",
              "stored", "decoded", "data", "data_stored", "data_decoded"]
    args.tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.tsv.open("w") as out:
        out.write("\t".join(fields) + "\n")
        for row in rows:
            out.write("\t".join(str(row[field]) for field in fields) + "\n")

    print(f"entries {len(rows)} in {stats['packs']} packs")
    print(f"  declared_ok packs {stats['declared_ok']}, short {stats['declared_short']}")
    for shape in ("pair", "header_only", "unpaired_large"):
        print(f"  {shape}: {stats[shape]}")
    decoded = sum(row["decoded"] for row in rows) + sum(row["data_decoded"] or 0 for row in rows)
    print(f"  decoded bytes covered: {decoded:,}")
    print(f"wrote {args.tsv}")


if __name__ == "__main__":
    main()
