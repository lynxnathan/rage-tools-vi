# rdna2-spirv journal

Append-only. Newest entries at the end.

## 2026-11-22 — M0: first end-to-end unit test

New workstream `rdna2-spirv/`: a generic GFX10.x decompiler. M0 is the plumbing
test — bytes in, valid SPIR-V out — not translation.

### What was built

`rdna2-spirv/tools/isa2spv.py` parses AMD's machine-readable ISA XML (MIT,
`amdgpu_isa_rdna2.xml`, 11.2 MB, 42 encodings, 3,156 instruction encodings),
decodes a stream, and emits one SPIR-V 1.5 module per unit with the decoded
stream as debug line info and a trivial compute entry point. Two details that
mattered:

- The XML `EncodingIdentifierMask` marks the bits the *format* fixes, not the
  opcode field. The opcode field is the set of bits that differ between the
  encoding's identifiers. Deriving it that way fixed SOPP, where the mask fixes
  bits 31:16 while the opcode lives at 21:16.
- A trailing literal word is present only when an operand selects it; a one-word
  lookahead decides between the short and long form.

`rdna2-spirv/tests/run_corpus.sh` runs the pipeline over a directory and
validates every emitted module with `spirv-val`.

### Decoder correctness, against LLVM

Eight instructions assembled by `llvm-mc --mcpu=gfx1030` all decode to the right
mnemonic and size, including the literal forms:

| Instruction | Encoding | Ours |
| --- | --- | --- |
| `s_endpgm` | `BF810000` | S_ENDPGM/4 |
| `s_mov_b32 s0,s1` | `BE800301` | S_MOV_B32/4 |
| `v_add_f32_e32 v1,v2,v3` | `06020702` | V_ADD_F32/4 |
| `s_load_dwordx2` | `F4040001 FA000000` | S_LOAD_DWORDX2/8 |
| `buffer_load_dword` | `E0301000 80010102` | BUFFER_LOAD_DWORD/8 |
| `ds_write_b32` | `D8340000 00000201` | DS_WRITE_B32/8 |

The strongest check is a real shader: `tests/fixtures/k.ll` compiled with
`llc -mcpu=gfx1030` yields 320 bytes; our decoder returns 75 instructions whose
first 13 (offset, size, mnemonic) are identical to `llvm-objdump`, followed by
`S_ENDPGM` and `S_CODE_END` padding — which is what that padding is.

### The corpus test

Output modules validate: 100 % of a 300-module random sample from the full run,
and 201/201 in the 60-page slice, pass `spirv-val --target-env vulkan1.2`.

Two runs over `shaders.rpf` (4,205 zlib streams, 275.5 MB):

| Mode | Units | Instructions | ISA coverage | SPIR-V |
| --- | ---: | ---: | ---: | ---: |
| carve, min 8 | 1,054,214 | 39,564,350 | 76.8 % | 4.2 GB |
| carve, min 16 (60 pages) | 0 | 0 | 0 % | 0 |

### The finding that matters

**The zlib streams in `shaders.rpf` are not RDNA2 code.** Longest decodable run
across sampled pages is 4–6 instructions; at a 16-instruction threshold a
60-page slice yields nothing. The one page that decodes from offset 0 to 8,192
instructions (`1068b8a0.bin`) contains only `V_ADD_F32` (4,685) and `V_SUB_F32`
(3,507) — a generated table, not a shader.

The reason the min-8 run reports 76.8 % coverage is that **RDNA2 encodings are
dense**: 82 % of uniformly random 32-bit words match some encoding (median over
4,205 pages of 81.6 % valid words). "It decoded" is therefore not evidence of
code, and a carve threshold alone cannot separate code from data. Decoder
agreement with LLVM is the only trustworthy gate, which is why M0 is built
around that comparison and why the corpus number is reported as coverage, not as
success.

### Next

The container adapter is now the blocker: the first stream in the pack begins
with `PS\x00\x09` (the PSO cache) and the rest are 64 KiB pages with
record-shaped headers, not instruction streams. Until the adapter extracts real
program bodies, corpus-level decode rates measure the container, not the ISA.
