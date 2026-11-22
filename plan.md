# Plan

Live check/todo list only. **Do not record findings here.** Evidence,
measurements, and narratives go in [investigation.md](investigation.md)
(append-only journal) and in `handoff/`. The research record that had
accumulated in this file was relocated to the journal on 2026-11-21.

Last updated: 2026-11-21.

## Now

- [ ] **Verify `levels.rpf` and rebuild the browser.** Extraction finished:
  1,117,857 streams / 174.9 GB. Verification is running; then
  `tools/pipeline.py --source SRC --output output pilot` so no archive is
  index-only in the browser.
- [ ] **Overnight unified pass** once `levels` is done: exact `+0xa0` harvest
  gated to the 208-byte bvh4 table, plus the struct-root/segment harvest across
  all archives. `cache/` on the NVMe is the scratch location.
- [ ] **Close the remaining `data.rpf` chain excess** (now known to be genuine
  multi-chain entries: `0xb07000` has 361 chains over 147 rows, `0x15000`
  exactly 1 chain per entry). Needs entry grouping inside multi-chain packs.
- [ ] ~~Explain the +2…+6 chain excess~~ — resolved: the linker is clean and
  the excess is genuine multi-chain entries, so this is folded into the item
  above.
- [ ] **Model directory/virtual rows in the entry count.** `data.rpf`'s root
  has 699 table rows (Front B = `align16(10 × 699)`) but 41 children and 0 own
  streams, so ≥658 rows carry no payload; `common.rpf` shows the same shape
  (418 vs 394). Solve the row model, then retry the extents resolver.
- [ ] ~~Replace saturation gating with a scored end-choosing DP~~ — implemented
  (`--dp`) and it converges with the saturation walk; the blocker is directory
  rows, not the selection rule.
- [ ] **Replace saturation gating with a scored end-choosing DP.** Pick each
  pack's end from the padding-candidate list by minimising `|items(end) - N|`
  under a containment constraint. `navmeshes` proved the need: homogeneous pair
  packs resolve (2,449 = 2,447 structs) but mixed packs (N = 3,224 with 3,109
  structs) never saturate and nest into a chain.
- [ ] **Define N per archive before the count oracle can generalise.**
  `tools/pack_extents.py` gives 16-aligned ends everywhere it has run
  (`textures` 21/21, `data` 42/42) but exact counts only where N counts direct
  items (`textures` 17/21; `data` 11/42 because its root declares 699 while
  holding 41 child packs and 0 own streams). Establish, per archive, whether N
  counts leaf entries, child packs, or a recursive total, then resume
  `navmeshes` and `data`.
- [ ] **Explorer (`explorer/`)**: finish the paged hierarchy, wire export
  cancellation, strengthen archive/index provenance beyond sampled identity,
  add asset previews, and measure throughput on the largest archives. Verify
  resumable indexing on other filesystems and operating systems.
- [ ] **Publish the full `core_bvh4` descriptor inventory** (269,106 entries:
  two ids, basis, true payload size, data stream). Run when the disk is free.
- [ ] **Identify the two `core_bvh4` descriptor ids** at `+0x40`/`+0x44` and the
  `u16` pair at `+0xa4` (bounded like an offset pair, role open).
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
- [ ] **Name the remaining 183 ped-rig hashes** (99 of 282 done; root
  `0x48dcbb01` fully decoded at 34/34). Mirror offsets (+25/+17/+12) plus
  neighbouring-muscle vocabulary at exact indices is the sharpest query left.
- [ ] **Crack the 330-hash unnamed universe** (31 roots). It is disjoint from the
  ped namespace and resists prefix sweeps, `part_position` forms and numeric
  patterns; needs a different vocabulary source.
  and three families (`skel_`, `mh_`, `rb_`), with a constant per-root `l`/`r`
  index offset (+25, +17, +12). Grow the anatomy/rig vocabulary, use the mirror
  offset to annotate unknown mirrors, and validate against the ordered families.
  See `handoff/bone-hash-names.tsv`.
- [ ] **Name the `0x8f18aff0` weight hashes**: the 57 shared bone hashes and the
  195 other hashes, then join weights to vertices/parts.

## Next

- [ ] **Decode the struct field map per size class.** The `{ptr, u16 count, u16
  cap}` containers are byte-identical within a size class, but the record size
  is not a clean function of the count; identify the remaining varying field.
- [ ] **Map the type/class IDs and transforms.** Group property/key IDs by
  parent/child shape, use the bone corpus to name part records, and decode the
  value entries and packed transform representation.
- [ ] **Name the `0x8f18aff0` pair namespace** and decide whether the
  high-1/high-2 pairs are endpoints, layers, or sides. (The 612 bone hashes are
  JOAAT of `skel_` names — see the Now item.)
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
