#!/usr/bin/env bash
# End-to-end unit test: ISA bytes in, SPIR-V out, every module validated.
#
#   rdna2-spirv/tests/run_corpus.sh [spec] [corpus-dir] [out-dir]
#
# Environment:
#   CARVE=0      treat inputs as raw ISA instead of carving containers
#   MINIMUM=n    minimum instruction count for a carved unit (default 8)
#   JOBS=n       parallel validations (default 8)
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2

SPEC=${1:-cache/rdna2/specs/amdgpu_isa_rdna2.xml}
CORPUS=${2:-cache/rdna2/corpus}
OUT=${3:-cache/rdna2/spv-test}
CARVE=${CARVE:-1}
MINIMUM=${MINIMUM:-8}
JOBS=${JOBS:-8}

[ -f "$SPEC" ] || { echo "missing spec: $SPEC" >&2; exit 2; }
[ -d "$CORPUS" ] || { echo "missing corpus: $CORPUS" >&2; exit 2; }
mkdir -p "$OUT"

args=()
[ "$CARVE" = 1 ] && args+=(--carve --minimum "$MINIMUM")

python3 rdna2-spirv/tools/isa2spv.py --spec "$SPEC" --input "$CORPUS" \
    --out "$OUT" --report "$OUT/report.tsv" "${args[@]}" || exit 1

total=$(find "$OUT" -name '*.spv' | wc -l)
echo "validating $total modules with spirv-val..."
find "$OUT" -name '*.spv' -print0 \
    | xargs -0 -n1 -P"$JOBS" sh -c 'spirv-val --target-env vulkan1.2 "$0" 2>/dev/null || echo "$0"' \
    > "$OUT/invalid.txt" 2>/dev/null
bad=$(wc -l < "$OUT/invalid.txt")

echo "modules: $total   valid: $((total - bad))   invalid: $bad"
if [ "$bad" -gt 0 ]; then
    echo "first invalid modules:"
    head -5 "$OUT/invalid.txt"
    exit 1
fi
[ "$total" -gt 0 ] || { echo "no modules emitted" >&2; exit 1; }
echo "PASS"
