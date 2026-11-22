# Plan

Milestones with testable acceptance criteria. The core is generic: every
milestone is stated against a target `--mcpu`, not against a game or a console. Nothing here is speculative about
feasibility: the two GPL projects in [PRIOR-ART.md](PRIOR-ART.md) already reach
the end of this ladder on neighbouring inputs.

## M0 — Decode tables and one shader

- [ ] Fetch the RDNA2 XML from GPUOpen (MIT) into `cache/` (never committed).
- [ ] `tools/gen_tables.py` emits instruction and operand tables for GFX10.3.
- [ ] Decode 64-bit SOP/VOP/SMEM and 32-bit VOP2/VOP1/VOPC/VINTRP words.
- [ ] Disassemble one real `shaders.rpf` stream to text.

**Accept:** for 100 randomly chosen instructions, our mnemonic and operand text
matches `llvm-mc --disassemble -triple=amdgcn -mcpu=gfx1030` after normalisation,
and `IsaDecoder` agrees on encoding fields.

## M1 — Full corpus decode

- [ ] All instruction families: SOP1/2/K/C, VOP1/2/3/C/3P, VINTRP, DS, SMEM,
  MUBUF, MTBUF, FLAT/GLOBAL/SCRATCH, MIMG, EXP, WAVE, and the RDNA2 ray-tracing
  additions.
- [ ] Every zlib stream in `shaders.rpf` disassembles to the end of its declared
  size with no unknown word.

**Accept:** ≥99.5 % of streams decode fully across at least two targets
(`gfx1030` and `gfx1013`); every failure is listed with its first undecodable
address and word.

## M2 — Control flow and EXEC

- [ ] CFG from branches (`s_branch`, `s_cbranch_*`, `s_setpc_b64`, indirect via
  `s_swappc_b64`), basic blocks, fallthrough.
- [ ] EXEC-mask tracking: `s_and_saveexec`, `s_or_saveexec`, `s_mov_exec`,
  `s_cbranch_execz` produce if/else and loop regions.
- [ ] Structured region tree (if/else, loops, break/continue) with no irreducible
  regions left unmarked.

**Accept:** the region tree for a hand-checked shader matches its HLSL/GLSL
source shape; loop trip counts are recoverable where the source used a constant.

## M3 — Lift to LLVM IR

- [ ] Value model: VGPR → `<lanes x i32>` SSA values, SGPR → uniform values,
  EXEC → per-instruction predicate mask, SCC/VCC → i1/i64.
- [ ] Arithmetic, bitfield, compare, select, conversions, LDS/scratch, buffer and
  image loads/stores with format conversion.
- [ ] Reference interpreter for the instruction subset, used as a differential
  oracle against the lifted IR on random inputs.

**Accept:** interpreter and lifted IR agree on 10^6 random inputs per instruction
group; the three hand-written shader fixtures produce identical final register
state.

## M4 — SPIR-V

- [ ] Emit SPIR-V 1.5 (baseline) and, behind a flag, AMDGCN-flavoured SPIR-V.
- [ ] `spirv-val` clean on every emitted module.
- [ ] Round-trip: emitted SPIR-V → `llc -mcpu=gfx1030` → ISA; compare against the
  original instruction sequence.

**Accept:** round-trip instruction match ≥95 % on the corpus with every mismatch
classified (scheduling, register allocation, or a lift bug).

## M5 — Corpus and editing

- [ ] Decode rate and stage mix reported for the whole corpus, generic streams
  and the repository's shader pack side by side.
- [ ] Editing demo: change a constant, reassemble at the original byte offsets,
  and show the resulting ISA differs only at that instruction.
- [ ] Publish a `docs/` page with the method, the numbers and the limits.

**Accept:** the edited shader passes the M4 gates and the diff is one instruction.

## Out of scope

- Reconstructing original HLSL source. The units are instructions and regions.
- Compiling for console hardware. Verification targets gfx1030 semantics via
  LLVM; hardware runs are optional.
- Container formats beyond a thin adapter. Parsing a PSO cache or an archive is
  the caller's job; this tool wants a byte range and a target.
- Recovering game-specific semantics (binding slots, root signatures). Those
  belong to whatever adapter supplies the descriptors.
