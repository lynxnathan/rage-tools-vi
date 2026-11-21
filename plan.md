# Plan

Live check/todo list only. **Do not record findings here.** Evidence,
measurements, and narratives go in [investigation.md](investigation.md)
(append-only journal) and in `handoff/`. The research record that had
accumulated in this file was relocated to the journal on 2026-11-21.

Last updated: 2026-11-21.

## Now

- [ ] **Finish `levels.rpf` extraction, verify, rebuild the browser.**
  1,117,857 streams / 174.9 GB, running on Mammoth (16 workers, `--resume`).
  Then `tools/pipeline.py --source SRC --output output verify` and `pilot`.
- [ ] **Explorer (`explorer/`)**: finish the paged hierarchy, wire export
  cancellation, strengthen archive/index provenance beyond sampled identity,
  add asset previews, and measure throughput on the largest archives. Verify
  resumable indexing on other filesystems and operating systems.
- [ ] **Resolve per-pack extents with an independent locator.** Needed for the
  pack hierarchy and per-pack entry coverage; the flat stream index cannot
  supply it (nested metadata merges into opaque spans). See the hierarchy
  attempt recorded in `investigation.md`.
- [ ] **Re-index the eight large archives** once, to pick up the corrected
  `chain_start` column (`tools/stream_index.py`).
- [ ] **Identify the extra Front B table `S` in mode families 2–8** (0 … 36 kB,
  16-byte aligned; family 4 is 224 B/entry ±8). Candidate: directory or
  resource-descriptor table. Test against packs with known child counts.
- [ ] **Boundary probe for the 9→10 byte stride flip.** A pack with N = 255 or
  256 separates a per-record index (9 B, max N−1) from a per-record count
  (10 B). This build has neither count; needs another build or a PC sample.
- [ ] **Test the four `+0x50` header profiles as cipher parameters**, and look
  for a known-plaintext crib; fall back to independent key material.
- [ ] **Front A milestone on `story000_bvh4.rpf`.** Four exact XML ranges; no
  offset/size pair found in the tested layouts. Resume with independent table
  framing or a plaintext record that predicts both endpoints.
- [ ] **Resolve the exact end of the last `data.rpf` child (bus #0151).**
  Bounded at or before `0x1cab4000`; reopen with an independent trailer start or
  a decoded parent entry. See `handoff/data-last-child.md`.
- [ ] **Multi-mip texture tail.** No descriptor with `+0x3e >= 2` exists in the
  corpus, so tail placement, mip order, and multi-mip pitch stay open. Reopen
  with a multi-mip dictionary. See `handoff/texture-mip-tail-blocker.md`.
- [ ] **Name the skeleton families.** Validate the bone hash namespace and
  order with an independently decoded model skeleton; resolve one fuzzy
  F05/F06 pair. See `handoff/script-bone-namespace-probe.md`.
- [ ] **Name the `0x8f18aff0` weight hashes**: the 57 shared bone hashes and the
  195 other hashes, then join weights to vertices/parts.

## Next

- [ ] **Map the type/class IDs and transforms.** Group property/key IDs by
  parent/child shape, use the bone corpus to name part records, and decode the
  value entries and packed transform representation.
- [ ] **Resolve the 612 class-0 bone-table hashes** (names or algorithm), name
  the `0x8f18aff0` pair namespace, and decide whether the high-1/high-2 pairs
  are endpoints, layers, or sides.
- [ ] **Resolve the 177 unnamed object roots** (79 vehicle-like, 86 class-0,
  12 other classes) from a model↔bone-list or `vehiclelayouts` mapping.
- [ ] **Finish the `data.rpf` boundary work**: final child end, opaque streams
  near `0x120d7000` and `0x1a279000`, per-language fronts vs shared trailers.
- [ ] **Reconcile `common.rpf` 394 candidate groups with `+0x24 = 418`**, and
  decode one directory node to confirm the directory hypothesis.
- [ ] **Name the unclassified payload bytes** (429.8 MB: shaders 274.0 MB,
  textures 136.0 MB, data 19.1 MB, script 431,696 B, common 210,272 B,
  appdata 5,216 B, core 4,976 B). See `handoff/unclassified-summary.tsv`.
- [ ] **Packs active-learning queue**: label representative/uncertain streams,
  then train a supervised classifier behind the deterministic verifier.
- [ ] **Opus pre-skip and end-trim** for AWC codec `0x0B`: establish pre-skip
  independently to split the current trim bound.
- [ ] **ACE1 trailer pairs**: assign the first trailer pair values beyond the
  final prefix block count.
- [ ] **Locate compiled shader bytecode**, if the corpus contains any; the
  marker scan was negative and SPS1 gives names only.
- [ ] **Script object root field roles** (`name`/flags/hash/heading/pointer) and
  the location of resolved transforms.
- [ ] **Verify any proposed entry record** against exact stored ranges and files
  split across multiple zlib streams.
- [ ] **Use recovered names, offsets, or plaintext hashes** as cribs for Front A
  and the trailer.

## Parked

- [ ] The 331,728-byte `script.rpf` blob and its seven-byte periodic islands.
  Revisit after a PC launch or a new sample.
- [ ] Full RPF9 metadata key recovery; needs key material or a second build.
