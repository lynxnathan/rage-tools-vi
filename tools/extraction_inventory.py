#!/usr/bin/env python3
"""Normalize existing extraction manifests into one repo-wide inventory."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

SCRIPT_EVIDENCE = []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-ranges", type=Path, default=Path("output/data.rpf/ranges.tsv"))
    parser.add_argument("--ranges-out", type=Path, default=Path("output/extraction-inventory.tsv"))
    parser.add_argument("--summary-out", type=Path, default=Path("handoff/extraction-inventory-summary.tsv"))
    args = parser.parse_args()

    rows = []
    totals = defaultdict(lambda: [0, 0, 0])
    if args.data_ranges.is_file():
        cursor = 0
        with args.data_ranges.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                start = int(row["start"], 16)
                end = int(row["end"], 16)
                stored = int(row["stored_bytes"])
                decoded = int(row["decoded_bytes"] or 0)
                if start != cursor or end <= start or end - start != stored:
                    raise SystemExit(f"broken coverage at {cursor:#x}: {row}")
                cursor = end
                kind = row["kind"]
                rows.append(("data.rpf", kind, start, end, stored, decoded, "output/data.rpf/ranges.tsv"))
                totals[("data.rpf", kind)][0] += 1
                totals[("data.rpf", kind)][1] += stored
                totals[("data.rpf", kind)][2] += decoded
        if cursor != 481544304:
            raise SystemExit(f"data.rpf coverage ended at {cursor}, expected 481544304")

    args.ranges_out.parent.mkdir(parents=True, exist_ok=True)
    with args.ranges_out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["archive", "kind", "start", "end", "stored_bytes", "decoded_bytes", "source"])
        for archive, kind, start, end, stored, decoded, source in rows:
            writer.writerow([archive, kind, f"0x{start:x}", f"0x{end:x}", stored, decoded, source])

    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["archive", "kind", "ranges", "stored_bytes", "decoded_bytes"])
        for (archive, kind), values in sorted(totals.items()):
            writer.writerow([archive, kind, *values])

    print("archive\tkind\tranges\tstored_bytes\tdecoded_bytes")
    for (archive, kind), values in sorted(totals.items()):
        print(archive, kind, *values, sep="\t")
    print("total", len(rows), sum(v[1] for v in totals.values()), sum(v[2] for v in totals.values()), sep="\t")


if __name__ == "__main__":
    main()
