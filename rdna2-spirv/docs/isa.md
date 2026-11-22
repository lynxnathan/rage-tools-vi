# GFX10.3 encoding notes

Summary of what the decoder has to handle. Field-level bit ranges come from
AMD's machine-readable ISA XML; this page is the structural overview and the
reasoning behind the IR choices.

## Instruction sizes

RDNA2 uses 64-bit instructions and 32-bit instructions in the same stream. The
size is a function of the opcode prefix:

| Words | Prefixes | Families |
| --- | --- | --- |
| 1 (32-bit) | scalar and short vector forms | `SOP1`, `SOP2`, `SOPK`, `SOPC`, `SOPP`, `VOP1`, `VOP2`, `VOPC`, `VINTRP` |
| 2 (64-bit) | long forms | `SOP2`, `VOP3`, `VOP3P`, `SMEM`, `MUBUF`, `MTBUF`, `DS`, `FLAT`/`GLOBAL`/`SCRATCH`, `MIMG`, `EXP`, `WAVE` (RDNA2 additions) |

A decoder must therefore commit to a size before it can read the next word;
unknown opcodes are fatal rather than skippable, which is why M1 requires a
100 %-clean corpus decode before any lifting starts.

## Scalar/vector split

- **SGPR** (`s0`–`s107`, wave-uniform): addresses, descriptors, constants,
  control. Lifts to uniform values.
- **VGPR** (`v0`–`v255`, per-lane): data. Lifts to `<lanes x i32>`.
- **Special**: `vcc` (vector compare, 64-bit), `scc` (scalar carry, 1-bit),
  `exec` (64-bit lane mask), `m0`, `flat_scratch`, `xnack_mask`, `tba`/`tma`.
- Constant-encoded GPRs: 106 `vcc_lo`, 107 `vcc_hi`, 124 `null`, 125 `m0`,
  126/127 `exec_lo/exec_hi`, 128+ literals (0, ±0.5, ±1, ±2, ±4,
  0x3e22f983, …). These literals are the fastest way to sanity-check a decoder:
  getting them wrong shifts every register operand by a constant.

## Execution model

RDNA2 is wavefront SIMD with a 32- or 64-lane wave. `EXEC` selects active lanes;
almost every vector instruction is `dst[lane] = active(lane) ? f(...) : dst[lane]`
— a **predicated write**, not a branch. Control flow is expressed as

```
s_and_saveexec_b64  sN, exec        ; sN = exec, exec = exec & condition
...
s_mov_b64           exec, sN        ; restore
```

so `if/else` and loop bodies must be reconstructed from `exec` state plus
`SCC`/`VCC` predicates. The lifted IR keeps the mask explicit; structuring it
into SPIR-V `OpSelectionMerge`/`OpLoopMerge` regions is M2.

## Memory

- `SMEM`: scalar loads from the constant descriptor in `s[base:base+1]`.
- `MUBUF`/`MTBUF`: strided buffer access; `MTBUF` carries a buffer data format
  that must be converted to a SPIR-V image format or an explicit unpack.
- `DS`: LDS/GDS, including the permute/broadcast variants.
- `FLAT`/`GLOBAL`/`SCRATCH` (same encoding family in GFX10): generic addressing.
- `MIMG`: image sampling with a 256-bit descriptor; sampler state in
  `s[base+4:base+7]`.

Buffer and image descriptors (`V#`, `T#`, `S#`) are 128-bit structures whose
format field matches `UfmtSymbolicGFX10` in LLVM — that mapping is public and is
what we use to pick SPIR-V image formats.

## Send/receive and other non-obvious pieces

- `s_sendmsg` / `s_sendmsghalt`: program end (`MSG_GS_DONE`, `MSG_HS_DONE`) and
  debug output. Termination is a message, not an instruction.
- `EXP`: export to the pixel shader output hardware; with `EXP prim` it is the
  NGG/mesh primitive export that identifies a mesh shader.
- `image_bvh64_intersect_ray`: hardware ray tracing; needs an emulation strategy
  rather than a direct SPIR-V mapping (SPIR-V has ray-query/trace instructions
  only through extensions).
- `s_swappc_b64`: indirect call. Requires the call-graph and the function table
  before a CFG is meaningful.

## What the IR must preserve

1. Instruction address and size (for reassembly).
2. Basic-block boundaries and the branch kind.
3. Register writes with their predicate (`exec`) so a later pass can re-derive
   the mask instead of trusting a re-synthesised one.
4. Original literal constants verbatim — floating-point literals in the ISA are
   bit patterns, not round-trippable decimals.
