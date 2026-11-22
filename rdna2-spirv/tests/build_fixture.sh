#!/usr/bin/env bash
# Rebuild the known-good ISA fixture: LLVM IR -> GFX10.3 machine code.
# Ground truth for the decoder, since the original instructions are known.
set -euo pipefail
cd "$(dirname "$0")/../.."
out=cache/rdna2/fixtures
mkdir -p "$out"
llc -march=amdgcn -mcpu=gfx1030 -filetype=obj \
    -o "$out/k.o" rdna2-spirv/tests/fixtures/k.ll
llvm-objcopy -O binary --only-section=.text "$out/k.o" "$out/k.bin"
echo "wrote $out/k.bin ($(stat -c%s "$out/k.bin") bytes)"
llvm-objdump -d --mcpu=gfx1030 "$out/k.o" | sed -n '/<k>:/,+14p'
