# rdna2-spirv

A generic AMD RDNA2 (GFX10.x) shader decompiler: machine code in, SPIR-V out.

The core is not tied to any game, platform, or container. It decodes GFX10.x
instruction streams and lifts them to SPIR-V, keeping byte offsets so an edited
program can be reassembled where it came from. Any container — a raw ISA blob, a
PSO cache entry, an archive stream — is an adapter in front of the same core.

The GTA VI shader pack in this repository is one test corpus among the generic
ones (LLVM's own disassembler tests, AMD's ISA examples, public Vulkan/GL
programs recompiled by hand). It is a consumer of this tool, not its definition.

## Why this is tractable

Nearly every piece already exists somewhere, and the most important piece is
MIT-licensed:

| Piece | Source | License |
| --- | --- | --- |
| Instruction encodings and semantics | [AMD Machine-Readable GPU ISA](https://gpuopen.com/machine-readable-isa/) (XML + `IsaDecoder`) | MIT |
| Independent decoder / encoder oracle | [LLVM AMDGPU](https://github.com/llvm/llvm-project/tree/main/llvm/lib/Target/AMDGPU) disassembler and TableGen definitions | Apache-2.0 WITH LLVM-exception |
| Target dialect | [AMDGCN-flavoured SPIR-V](https://rocmdocs.amd.com/projects/llvm-project/en/latest/conceptual/spirv.html) (`--offload-arch=amdgcnspirv`) | documentation |
| LLVM IR ↔ SPIR-V | [SPIRV-LLVM-Translator](https://github.com/KhronosGroup/SPIRV-LLVM-Translator) | LLVM exception |
| Validation | [SPIRV-Tools](https://github.com/KhronosGroup/SPIRV-Tools) `spirv-val` | Apache-2.0 |
| Forward path, for round-trip tests | `llc -march=amdgcn -mcpu=gfx1030` | Apache-2.0 WITH LLVM-exception |

See [PRIOR-ART.md](PRIOR-ART.md) for the projects that already attempt the same
thing, what they do, and their licences. Two of them (`AnyPS5`, `xcl`) are
GPL-2.0 and one (`PercyStar`) is all-rights-reserved, so this workstream is
written from the ISA documents and LLVM, not from their code.

## Sources policy

Every step is reproducible from public material only: AMD's machine-readable ISA
(MIT), LLVM, and the SPIR-V specification. No proprietary SDK, header, or NDA
document is a dependency, a deliverable, or an acceptance criterion. If licensed
material is ever consulted for a sanity check, it stays outside git and nothing
in the repository may require it.

## Design

The lift is *SPMD*, the same model hardware uses:

```
shader blob ──► decoder ──► MCInst stream ──► CFG + EXEC analysis
                                                   │
                                                   ▼
                            LLVM IR: VGPR v0..v255 → <lanes x i32>,
                                     SGPR s0..s107 → uniform values,
                                     EXEC/SCC/VCC → explicit mask state
                                                   │
                                                   ▼
                                    SPIR-V 1.5/1.6 (AMDGCN flavour)
                                                   │
                                                   ▼
                              spirv-val ──► llc -mcpu=gfx1030 ──► diff
```

Byte offsets and basic-block boundaries stay in the intermediate
representation, so an edited program can be reassembled at the original
addresses.

## Data

The core takes a byte range of ISA and a target `--mcpu` (`gfx1013`, `gfx1030`,
`gfx1031`, `gfx1032`, …). Everything platform-specific lives in an optional
container adapter; the repository ships a generic one (raw stream, length-prefixed
blob) and, as one adapter among several, a reader for the RPF9 shader pack that
lives in this repo.

That pack is useful because it is large, real, and mixed: 8,180 ranges, 4,205
zlib streams, 3,972 zero runs. Sampled streams begin with 64-bit
instruction-like words (for example `2b812b80 2f0082d4`). Shader payloads are
plaintext once the zlib layer is gone, so no archive work is needed to decode
them.

## Status

Research and plan only. See [PLAN.md](PLAN.md) for the milestone ladder and
acceptance criteria.

## Layout

```
rdna2-spirv/
├── README.md        this file
├── PRIOR-ART.md     what already exists, what we can reuse, what we cannot
├── PLAN.md          milestones with acceptance criteria
└── docs/
    ├── isa.md       GFX10.3 encoding notes (instruction formats, EXEC model)
    └── verification.md  why round-trip through LLVM is the oracle
```
