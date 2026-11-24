#!/usr/bin/env bash
# Produce playable audio from three AWC variants, repeatably.
#
#   tools/demo_media.sh [DEST]
#
# Fixed container offsets so the same bytes come out every run. Each WAV is checked for
# duration, level and spectral flatness; the manifest lists all of it.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=python3
command -v uv >/dev/null && [ -f pyproject.toml ] && PY="uv run python"
DEST=${1:-output/demo}
SRC=${SRC:-/home/lynxnathan/gta6-source/audio.rpf}
mkdir -p "$DEST"

# variant offset_start offset_end mode stream
runs=(
  "ff21 0x129b000 0x12a2000 stream 0"
  "ff02 0x16437000 0x16baa000 stream 0"
  "ff25 0x548f000 0x58af800 ff25 0"
)
for row in "${runs[@]}"; do
  set -- $row
  variant=$1; start=$2; finish=$3; mode=$4; stream=$5
  out="$DEST/$variant-$stream.wav"
  if [ "$mode" = "ff25" ]; then
    $PY tools/decode_adat_stream.py "$SRC" --start "$start" --end "$finish" \
        --ff25 --output "$out" >/dev/null 2>&1
  else
    $PY tools/decode_adat_stream.py "$SRC" --start "$start" --end "$finish" \
        --stream "$stream" --output "$out" >/dev/null 2>&1
  fi
  [ -f "$out" ] || { echo "FAIL $variant"; continue; }
done

$PY - "$DEST" <<'PY'
import sys, wave
from pathlib import Path
import numpy as np
dest = Path(sys.argv[1])
rows = ["file\tseconds\tchannels\trms\tflatness"]
ok = True
for path in sorted(dest.glob("*.wav")):
    with wave.open(str(path)) as w:
        n, ch, rate = w.getnframes(), w.getnchannels(), w.getframerate()
        x = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float32) / 32768
    seg = x[: min(len(x), rate)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) + 1e-12
    flat = float(np.exp(np.mean(np.log(spec))) / np.mean(spec))
    rms = float(np.sqrt((x ** 2).mean()))
    rows.append(f"{path.name}\t{n / rate:.2f}\t{ch}\t{rms:.4f}\t{flat:.4f}")
    ok = ok and n / rate > 0.2 and rms > 100 / 32768
print("\n".join(rows))
raise SystemExit(0 if ok else 1)
PY
