# Prior art

Surveyed 2026-11-22. Split by what we may *use* (licence-compatible) and what we
may only *learn from*.

## Permissive: use directly

### AMD Machine-Readable GPU ISA — MIT

- Spec portal: <https://gpuopen.com/machine-readable-isa/>
- Tools and schema: <https://github.com/GPUOpen-Tools/isa_spec_manager>
- Schema docs: `documentation/spec_documentation.md` in that repo
- Blog walkthrough: <https://gpuopen.com/learn/using-isadecoder-api/>

XML files describe instructions, encodings (bit ranges, operand fields), data
formats and human-readable descriptions for RDNA1/2/3/3.5/4 and CDNA1–5. This is
the primary source for our decode tables. The `IsaDecoder` C++ API in the same
repo decodes single instructions and whole kernels, which gives a second,
independent decoder for testing.

### LLVM AMDGPU backend — Apache-2.0 WITH LLVM-exception

- Disassembler: `llvm/lib/Target/AMDGPU/Disassembler/AMDGPUDisassembler.cpp`
- Instruction definitions: `llvm/lib/Target/AMDGPU/*Instructions.td`,
  `MCTargetDesc/AMDGPUInstPrinter.cpp`
- Usage as an oracle:
  `llvm-mc --disassemble -triple=amdgcn -mcpu=gfx1030 --show-encoding`

Two uses: a reference decoder to compare against, and the *forward* compiler for
round-trip verification.

### SPIRV-Tools / SPIRV-LLVM-Translator — Apache-2.0 / LLVM exception

`spirv-val` for validity, `spirv-dis`/`spirv-as` for diffing, and the translator
for LLVM IR → SPIR-V once the lift produces LLVM IR.

### Radeon GPU Analyzer (RGA) — MIT

<https://github.com/gpuopen-tools/radeon_gpu_analyzer>

Offline compiler with ISA disassembly for GCN/RDNA. Useful as a third
disassembly opinion for code paths we compile ourselves.

### tinygrad `test/amd/disasm.py`

<https://github.com/tinygrad/tinygrad/blob/master/test/amd/disasm.py>

A compact pure-Python RDNA3/RDNA4/CDNA disassembler, including special-GPR
mapping and DPP16 decoding. Not our target arch, but the clearest short example
of the field layout in code.

## Copyleft / closed: learn only

### AnyPS5 — GPL-2.0-only

<https://github.com/boykopovar/AnyPS5>

Closest prior art. It recompiles PS5 shaders (gfx1013, RDNA2-class) to SPIR-V
and validates with SPIRV-Tools. Its README shows two progress badges: "RDNA2
reference shader forms decoded" and "gfx1013 reference shader forms decoded", and
the recompiler lives at `core/shader/recompiler/Recompiler.cpp`.

We do not copy it (GPL-2.0 would bind this repository), but it establishes that
RDNA2 → SPIR-V is achievable and that SPIRV-Tools validation is the right gate.

### XCL — GPL-2.0-only

<https://github.com/ivall/xcl>

RDNA2 → HLSL → DXIL for a retail Xbox Series X game: 24,064 of 24,064 shader
programs translate, with per-instruction GPU tests and structured control flow.
Its `THIRD_PARTY.md` documents exactly how it generates its instruction tables:
`scripts/gen_rdna2.py` consumes AMD's machine-readable ISA into
`crates/xcl/src/gpu/rdna2_spec.rs`. That generator pattern is the one we will
follow, written independently.

Also documents the container side (`xcl disasm <shader.bin>` handles "console
shader containers") and the practical instruction families a full shader needs:
atomics, LDS, scratch, images, samplers including static ones, wave ops,
ray-tracing instructions.

### PercyStar — all rights reserved

<https://github.com/rpatty-dev/PercyStar>

Rust tool that parses the Xbox Series X `PS\x00\x09` PSO cache (25,471 graphics
PSOs, 2,693 compute PSOs, 21,522 GFX10.3 shaders), disassembles, and lifts to
"HLSL SM 6.6" and "SPIR-V 1.5 / SGPR ABI". Its README states the licence forbids
modified redistribution, so it is a reference for *what the output should look
like*, not a source.

Notably it claims stage tagging by instruction: NGG/mesh via `exp prim`, hardware
ray tracing via `image_bvh64_intersect_ray`.

### Xbox2Windows — MIT (adjacent, same game)

<https://github.com/R0Y00/Xbox2Windows>

GTA VI static recompilation research. Useful context for the shader container
and PSO layout, not for the ISA layer.

## Related but different

- **XShaderRecomp** — original Xbox (NV2A) shaders to HLSL; wrong ISA.
- **Mesa radv/ACO** — the forward path (SPIR-V → NIR → RDNA2 ISA). Its NIR
  lowering shows what each ISA instruction is supposed to mean, which is the
  best semantic cross-check for our lift in the other direction.

## What is left for us

1. An open, documented pipeline that targets **SPIR-V directly** for **Xbox
   Series X GFX10.3** (`PS\x00\x09` containers, `shaders.rpf`), not HLSL-via-DXC.
2. Decode tables generated from AMD's MIT XML, with LLVM as an independent
   decoder oracle and a published match rate.
3. Round-trip verification: original ISA → SPIR-V → `llc -mcpu=gfx1030` → ISA,
   compared instruction by instruction.
4. Byte offsets preserved so edited shaders can be reassembled.
