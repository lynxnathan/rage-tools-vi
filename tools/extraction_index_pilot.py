#!/usr/bin/env python3
"""Build a local RPF range browser from the rebuilt audio and levels TSVs."""

import argparse
import csv
import hashlib
from itertools import islice
import json
from pathlib import Path

from extraction_tree import HTML


OUTPUT = Path("output")
AUDIO_INDEX = OUTPUT / "index/audio.tsv"
LEVELS_INDEX = OUTPUT / "index/levels.tsv"
AUDIO_MANIFEST = OUTPUT / "extracted/audio/manifest.tsv"
VERIFICATION = OUTPUT / "verification.tsv"
PAGE_SIZE = 32


def rows(path):
    with path.open(encoding="utf-8", newline="") as source:
        yield from csv.DictReader(source, delimiter="\t")


def extent(row):
    return tuple(int(row[field], 16) for field in ("start", "end"))


def range_item(row, archive, extracted=None):
    start, end = extent(row)
    status = "Unresolved" if row["kind"] == "unclassified" else "Indexed only"
    item = {
        "name": f"{start:#x}–{end:#x}",
        "kind": f"{status} · {row['kind']}",
        "start": start,
        "end": end,
        "stored": int(row["stored_bytes"]),
        "decoded": int(row["decoded_bytes"] or 0),
        "source": archive,
        "availability": "No extracted file is listed for this range.",
    }
    if extracted:
        item.update(kind=f"Decoded / verified · {row['kind']}",
                    file=extracted["path"], sha256=extracted["sha256"],
                    manifest=str(AUDIO_MANIFEST), availability="")
    return item


def audio_root():
    records = list(rows(AUDIO_MANIFEST))
    manifest = {extent(row): row for row in records}
    checks = [row for row in rows(VERIFICATION) if Path(row["archive"]).name == "audio.rpf"]
    if (len(checks) != 1 or checks[0]["status"] != "PASS"
            or int(checks[0]["manifest"]) != len(records) or len(manifest) != len(records)):
        raise ValueError("Audio manifest lacks a matching PASS verification record")

    source = checks[0]["archive"]
    entries = []
    for row in rows(AUDIO_INDEX):
        extracted = manifest.pop(extent(row), None)
        if extracted and (row["kind"] != "zlib" or any(
            int(row[field]) != int(extracted[field]) for field in ("stored_bytes", "decoded_bytes")
        )):
            raise ValueError(f"Audio index and manifest disagree at {row['start']}")
        entries.append(range_item(row, source, extracted))
    if manifest:
        raise ValueError("Some audio manifest extents are absent from the index")

    control = next(entry for entry in entries if "sha256" in entry)
    control_path = Path(control["file"])
    with control_path.open("rb") as payload:
        actual = hashlib.file_digest(payload, "sha256").hexdigest()
    if control_path.stat().st_size != control["decoded"] or actual != control["sha256"]:
        raise ValueError(f"Audio control failed size/hash verification: {control_path}")
    print(f"audio {control['name']} matched the decoded file and SHA-256 {actual}")
    return {"name": "audio.rpf", "kind": "Verified archive · all indexed ranges",
            "children": entries}


def levels_root():
    with LEVELS_INDEX.open("rb") as index:
        total = sum(1 for _ in index) - 1
    if total <= 0:
        raise ValueError("Levels index is empty")
    starts = sorted({0, max(0, (total - PAGE_SIZE) // 2), max(0, total - PAGE_SIZE)})
    pages = []
    cursor = 0
    index_rows = rows(LEVELS_INDEX)
    for start in starts:
        if start < cursor:
            continue
        page = [range_item(row, "levels.rpf") for row in
                islice(index_rows, start - cursor, start - cursor + PAGE_SIZE)]
        cursor = start + len(page)
        pages.append({"name": f"Index rows {start + 1:,}–{cursor:,}", "kind": "Sample page",
                      "children": page})

    sampled = sum(len(page["children"]) for page in pages)
    control = next(item for page in pages for item in page["children"]
                   if item["kind"] == "Indexed only · zlib")
    if (OUTPUT / "extracted/levels/manifest.tsv").exists():
        raise ValueError("Levels now has a bulk extraction manifest; update the pilot before using it")
    print(f"levels {control['name']} matched the index; no bulk extraction manifest")
    return {"name": "levels.rpf", "kind": "Indexed only · sampled ranges", "children": pages,
            "note": f"Showing {sampled:,} of {total:,} index ranges in bounded sample pages. "
                    f"Full index: {LEVELS_INDEX}. Pack membership is unresolved."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT / "extraction-index-pilot/index.html")
    args = parser.parse_args()
    roots = [audio_root(), levels_root()]
    data = json.dumps(roots, separators=(",", ":"), ensure_ascii=True).replace("<", "\\u003c")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(HTML.replace("__ARCHIVES__", data), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
