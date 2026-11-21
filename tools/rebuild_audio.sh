#!/usr/bin/env bash
# Rebuild every generated audio.rpf artifact from the source archive.
# Usage: PYTHON=/path/to/python tools/rebuild_audio.sh SOURCE_AUDIO_RPF [OUTPUT_EXTRACTED]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${1:?usage: rebuild_audio.sh SOURCE_AUDIO_RPF [OUTPUT_EXTRACTED]}"
OUT="${2:-$ROOT/output/extracted}"
PYTHON="${PYTHON:-python3}"
START="${START:-0x129b000}"

[[ -f "$SOURCE" ]] || { echo "missing source: $SOURCE" >&2; exit 1; }
END="$(stat -c %s "$SOURCE")"
cd "$ROOT"

rm -rf "$OUT/audio-awc" "$OUT/audio-xma2"
mkdir -p "$OUT/audio-awc" "$OUT/audio-xma2"

python3 tools/extract_awc.py "$SOURCE" \
  --start "$START" --end "$END" \
  --out-dir "$OUT/audio-awc" \
  --manifest "$OUT/audio-awc/manifest.tsv"

python3 tools/awc_framing.py --limit 0

"$PYTHON" tools/extract_awc_xma2.py --limit 0 --out "$OUT/audio-xma2"

python3 - "$OUT" <<'PY'
import csv
import sys
from pathlib import Path

out = Path(sys.argv[1])
awc = list(csv.DictReader((out / "audio-awc" / "manifest.tsv").open(), delimiter="\t"))
xma2 = list(csv.DictReader((out / "audio-xma2" / "manifest.tsv").open(), delimiter="\t"))
wavs = list((out / "audio-xma2").glob("*.wav"))
print(f"awc={len(awc)} xma2_rows={len(xma2)} xma2_ok={sum(not r.get('error') for r in xma2)} wavs={len(wavs)}")
if len(awc) != 6625:
    raise SystemExit(f"unexpected AWC count: {len(awc)}")
if len(wavs) != 151:
    raise SystemExit(f"unexpected XMA2 WAV count: {len(wavs)}")
PY
