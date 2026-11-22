# Plan

Live check/todo list only. **Do not record findings here.** Evidence,
measurements, and narratives go in [investigation.md](investigation.md)
(append-only journal) and in `handoff/`. Completed items leave this file; their
evidence stays in the journal.

Last updated: 2026-11-21.

## Now

Five items, all actionable with what is on disk today.

- [ ] **Finish the `core_bvh4` descriptor inventory.** `handoff/core-bvh4-descriptors.tsv`
  has 269,106 rows (ids, exact `+0xa0`, `+0xa4` pair) but no basis. One more pass
  adds the three orientation rows; also harvest `shared_minigame000_bvh4`
  (1,280 descriptors) so both bvh4 archives are covered.
- [ ] **Name the remaining 183 ped-rig hashes.** 99 of 282 done, one rig fully
  decoded. Method that works: curated anatomy vocabulary ×
  `<skel_|mh_|rb_><side><part><00–99>` with the per-root mirror offsets
  (+25/+17/+12) used to target the right indices. Grow the vocabulary, do not
  guess the hash.
- [ ] **Open the 330-hash universe with a new name source.** The 31 unnamed roots
  are disjoint from the ped namespace and resist anatomy words, vehicle
  `part_position` forms and numeric patterns. Harvest text from the archives that
  just became local (`levels` extraction, `textures`, `shaders`) and test
  JOAAT/CRC32 plus the `ik_`-style compound forms seen in the corpus
  (`ik_l_foot_dside_r`).
- [ ] **Repoint `tools/extraction_inventory.py` at the manifests.** It still reads
  the pre-rebuild `output/data.rpf/ranges.tsv` and produces an empty inventory;
  the manifests are the authoritative coverage record (2,199,594 streams /
  360,572,388,767 decoded).
- [ ] **Rehash all of `levels`** (175 GB) for a full verification instead of the
  completeness pass plus 1,500-file sample.

## Next

- [ ] **Test the weight hashes against rig names.** The 252 `0x8f18aff0` hashes
  were probed before the `skel_`/`mh_`/`rb_` convention existed; re-test with the
  decoded 99 names and their generated neighbours.
- [ ] **Re-index the eight large archives** once, to pick up the corrected
  `chain_start` column (`tools/stream_index.py`).
- [ ] **Validate the skeleton families with the decoded rig.** `0x48dcbb01` is a
  complete two-sided hand/forearm rig; use it to confirm the family clustering
  and the mirror-offset rule across the other named roots.
- [ ] **Map the type/class IDs and transforms.** Group property/key IDs by
  parent/child shape, use the bone corpus to name part records, and decode the
  value entries and packed transform representation.
- [ ] **Resolve the 177 unnamed object roots** (79 vehicle-like, 86 class-0,
  12 other classes) from a model↔bone-list or `vehiclelayouts` mapping.
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

## Blocked

Each item states the condition that would unblock it. Nothing here is waiting on
effort, only on information the corpus does not yet expose.

- [ ] **Directory/virtual rows in the entry count.** `data.rpf`'s root is 699
  rows = 41 child packs + 658 virtual, and `common.rpf` shows 418 vs 394. The row
  type lives in masked Front B, so this needs key material or a crib. Until then
  the extents resolver cannot generalise past leaf packs.
- [ ] **Multi-chain entry grouping** (`0xb07000`: 361 chains over 147 rows).
  Needs one decoded per-entry marker inside such a pack.
- [ ] **Front B table `S`** in mode families 2–8 (0 … 36 kB, 16-byte aligned;
  family 4 is 224 B/entry ±8). Same mask problem.
- [ ] **9→10 byte stride boundary.** Needs a pack with N = 255 or 256, i.e.
  another build or a PC sample.
- [ ] **Four `+0x50` header profiles as cipher parameters.** Needs a
  known-plaintext crib or key material.
- [ ] **Front A milestone on `story000_bvh4.rpf`.** Four exact XML ranges, no
  offset/size pair in the tested layouts; needs independent table framing or a
  plaintext record predicting both endpoints.
- [ ] **Exact end of the last `data.rpf` child (bus #0151).** Needs an independent
  trailer start or a decoded parent entry; `handoff/data-last-child.md`.
- [ ] **Multi-mip texture tail.** No descriptor with `+0x3e >= 2` exists in the
  corpus; needs a multi-mip dictionary.
- [ ] The 331,728-byte `script.rpf` blob and its seven-byte periodic islands.
  Revisit after a PC launch or a new sample.
- [ ] Full RPF9 metadata key recovery; needs key material or a second build.

## Not mine

- [ ] **Explorer (`explorer/`)** — another model owns this session's work:
  paged hierarchy, provenance beyond sampled identity, asset previews,
  large-archive throughput, cross-filesystem resume.
