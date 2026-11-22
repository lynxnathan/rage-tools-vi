# Verification

A decompiler that cannot be checked is a guess. Three independent checks, in
increasing strength.

## 1. Decode agreement

Two decoders that share no code must agree on every instruction:

- ours, generated from AMD's machine-readable ISA XML;
- LLVM's, `llvm-mc --disassemble -triple=amdgcn -mcpu=gfx1030 --show-encoding`.

For each word we compare mnemonic, operand list, and encoding fields. A mismatch
is either a table bug or an ambiguous encoding (literals and the special GPR
aliases are the usual suspects). `IsaDecoder` from GPUOpen gives a third opinion;
agreement between three independent implementations is strong evidence the
decoder is right, independent of any game.

## 2. Lift agreement

Two ways to run the same program and compare final state:

- a reference interpreter over the ISA (direct, obviously correct, slow);
- the lifted SPIR-V, executed on any Vulkan implementation, or the lifted LLVM IR
  compiled for the host.

Random inputs per instruction group, plus the corpus fixtures, give
`interpret(isa) == run(spirv)` as a bit-exact predicate per register. This is the
step that catches semantic bugs the decoder comparison cannot see: wrong
rounding on conversions, wrong saturate, wrong `exec` predication, wrong
bitfield insert.

## 3. Round trip through LLVM

The strongest structural check, because it goes all the way back to hardware
code:

```
ISA  ──decode──►  our IR  ──lift──►  SPIR-V  ──llc -mcpu=gfx1030──►  ISA'
```

`spirv-val` must pass first. Then `ISA'` is compared to `ISA` instruction by
instruction. Perfect equality is not expected — different register allocators and
schedulers produce different but equivalent code — so mismatches are classified:

| Class | Meaning |
| --- | --- |
| scheduling | same instructions, different order |
| allocation | same operations, different registers |
| folded | the compiler merged an instruction (e.g. `v_mul` + `v_add` → `v_fma`) |
| **lift bug** | semantics differ; must be fixed |

The gate is not "identical ISA" but "no unclassified diffs". A shader whose
round trip only shows scheduling and allocation differences is evidence the lift
preserved meaning.

## Why not just compare to the original source

Because there is none. Console shader packs ship machine code; the high-level
language and its compiler are gone. Any "source" we printed would be a rendering
of our own IR, and comparing a decompiler to itself proves nothing. The three
checks above are all anchored to something outside our implementation: AMD's
spec, LLVM's decoder, and LLVM's compiler.

## Fixtures

- LLVM's own AMDGPU disassembler tests — public, per-instruction, already in
  text form with expected encodings.
- AMD ISA XML examples.
- Hand-written GLSL/HLSL compiled with `llc -mcpu=gfx1030`, where the input
  semantics are known by construction.
- One real, large, mixed corpus (the shader pack in this repo) for scale.
