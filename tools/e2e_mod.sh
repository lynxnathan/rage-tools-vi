#!/usr/bin/env bash
# End-to-end mod check: replace an asset in a copy of an archive, then prove the copy
# still parses and the new bytes are what a reader gets.
#
#   tools/e2e_mod.sh [ARCHIVE] [START] [END]
set -uo pipefail
cd "$(dirname "$0")/.."
PY=python3
command -v uv >/dev/null && [ -f pyproject.toml ] && PY="uv run python"

ARCHIVE=${1:-common.rpf}
START=${2:-0x3b2850}
END=${3:-0x3b399e}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
COPY="$TMP/mod.rpf"
cp "$ARCHIVE" "$COPY"
before=$(stat -c%s "$COPY")

$PY tools/mod_replace.py "$COPY" --start "$START" --end "$END" --marker "E2E_OK" >/dev/null || exit 1
$PY tools/stream_index.py "$COPY" --out "$TMP/index.tsv" >/dev/null || exit 1

$PY - "$ARCHIVE" "$COPY" "$TMP/index.tsv" "$START" "$END" <<'PY'
import csv, sys, zlib
from pathlib import Path
archive, copy, index, start, end = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4], 0), int(sys.argv[5], 0)
size_before = Path(archive).stat().st_size
size_after = Path(copy).stat().st_size
data = Path(copy).read_bytes()
payload = zlib.decompress(data[start:end])
rows = list(csv.DictReader(open(index), delimiter="\t"))
covered = sum(int(r["end"], 16) - int(r["start"], 16) for r in rows)
ok = True
def say(name, cond, detail=""):
    global ok
    print(f"  {'ok  ' if cond else 'FAIL'}  {name} {detail}")
    ok = ok and cond
say("archive size unchanged", size_before == size_after)
say("payload replaced", payload == b"E2E_OK", payload[:16])
say("index still tiles the file", covered == size_after + 0, f"{covered} vs {size_after}")
say("range is still classified zlib",
    any(r["start"] == hex(start) and r["kind"] == "zlib" for r in rows))
sys.exit(0 if ok else 1)
PY
