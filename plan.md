# Plan

Current state and open work. Narrative, measurements and evidence belong in
[investigation.md](investigation.md) and `handoff/`. Completed work stays as one
line of state, not as a log.

Last updated: 2026-11-21.

## Current state

- **Extraction:** all 22 source archives indexed — 4,415,850 ranges / 161.3 GB
  stored / 365.0 GB decoded, every index tiling its archive exactly. Six
  archives plus `levels` carry bulk manifests (2,190,635 of 2,241,410 zlib
  ranges); the rest are analysed locally. `levels` verified (completeness pass
  plus a 1,500-file hash sample).
- **Unclassified:** closed. Every large span is media — 38.1 GB AWC audio,
  13.4 GB Bink/Bink2 video, ~1.2 GB fragments. No unexplained game payload.
- **Cutscene audio:** `story000`'s 9.56 GB AWC chain is extracted and decoded —
  **196,350 Opus streams / 148.3 hours / 47.7 GB of WAV** in
  `output/extracted/story000-opus/`. The `0xff02` layout (98.4 % of the chain)
  is solved; 210 containers of other variants remain undecoded.
- **Entry level:** payload-derived manifests cover four archives — 328,481
  entries with exact boundaries: `core_bvh4` (pairs, 1,214/1,282 packs),
  `navmeshes` (chains, 13/29), `data` (chains, 19/42), `textures` (pairs, 19/21).
  Unverified packs are exactly those whose entries mix shapes. All four
  manifests pass a self-consistency check (0 index-missing, 0 duplicates).
- **Descriptors:** both bvh4 archives inventoried — `core_bvh4` 269,106 rows and
  `shared_minigame000_bvh4` 1,233, with exact allocated sizes and an orthonormal
  right-handed basis (269,105/269,106 within 1e-3).
- **Pack extents:** zero-padding boundaries are exact and 16-aligned on every
  archive tested; leaf extents published; parents still need a row model.
- **Metadata:** header census complete (4,373 headers); Front A/Front B/trailer
  remain masked; size laws characterised.
- **Script:** `script.rpf` records are a section sequence
  (`PSIN`/`LSCH`/`LENM`/`LSNS`/`LGID`/`LRSC`/`CHKS`), not YSC. PSIN holds typed
  tables, LSNS (939 KB total) and the 331 KB blob are genuinely encrypted, and no
  cipher tables ship in the local binaries. Decomp research and pipeline design
  are recorded; decoding is key-blocked.
- **Naming:** all identifiers are `JOAAT(lowercase name)`. 99 of 612 bone-table
  hashes and 21 of 252 weight hashes resolved across `skel_`/`mh_`/`rb_`
  families; one rig fully decoded (34/34); the 16 skeleton families carry
  readings (hand, genital, large animal, small props). The 330-hash universe is
  the unnamed small-prop families.
- **Browser:** `output/extraction-index-pilot/index.html` rebuilt with seven
  verified archives.
- **Disk:** Mammoth at 95 % (188 GB free) after the 47.7 GB cutscene decode.

## Now

- [x] PSIN names are JOAAT32: 25 of 301 small-vocabulary hashes and 515 of
  14,653 large-vocabulary hashes resolve against the 174k corpus
  (`tools/psin_name_probe.py`, `handoff/psin-names.tsv`; 0.61 expected
  collisions against 540 hits).
- [x] PSIN record roles settled: small vocabulary = property name, large =
  object key (`location_*` keys carry two properties; a value cannot).
  Relabelled in the tool and `handoff/psin-names.tsv`.
- [x] `tools/psin_extract.py` produces the property dump directly from
  `script.rpf` (62,910 rows, identical to the earlier dump), so the chain
  archive -> dump -> lookup -> entries needs no external cache.
- [x] PSIN records render as entries: `tools/psin_segment.py --describe` pairs
  local `Id`/`Type` runs and resolves the payload from the key column, so record
  1054 reads as vehicle parts (bonnet, side, roof, cosmetics) and locations.
- [ ] Recover the parent/child relation by segmenting on **local table width**:
  four PSIN records are fixed-width tables (width 4 x3, width 6 x1, ≥99.7 %
  agreement), while the largest (6,246 rows) has no global period — the tree
  boundary is a change of period, not a hidden field. Segment the row stream
  where the local period changes.
  Widen the corpus to raise 25/301 properties and 515/14,653 keys.
- [x] Make names usable: `handoff/names.tsv` (646 names, confidence-ordered),
  `tools/name_registry.py` (build/lookup/annotate) and `tools/psin_dump.py`
  (schema in English). New hash sources plug into one `SOURCES` list.
- [ ] Script decomp pipeline is gated on key material. Section split and PSIN
  directory are done; PSIN blocks are typed tables (22–38 % invalid opcodes vs
  49 % random), and LSNS is genuinely encrypted (uniform entropy, deterministic,
  no weak structure, no cipher tables in the shipped binaries). Reopen when a key
  or a second sample appears; the crib is the content-dependent first block.

- [x] Rejected: naming bones by geometry. `tools/bone_geometry_names.py`
  leave-one-out scores 0 % — the stored geometry is bone-local, so mirrored bones
  are identical and neighbours are always the opposite side. Needs rig-space
  transforms, not more vocabulary.
- [ ] Name the remaining ped-rig bone hashes. A corpus sweep
  (`tools/rig_name_corpus_probe.py`) adds 4 candidates, but they need an
  independent predictor (mirror offset, table position) before promotion; the
  collision budget allows ~1.3 false hits per sweep of this size.
- [ ] Name the remaining weight hashes (21 of 252 done). A 174k-token corpus
  sweep over the 231 unnamed hashes yields one candidate (`ph_hat`, 0.22 expected
  false positives); the cheap vocabulary is now exhausted — needs another source.
- [ ] Open the 330-hash universe with a new vocabulary source. The corpus route
  is exhausted for *types*: 174k tokens against 35,106 type hashes returns 0 hits
  (1.42 expected by chance). The engine metadata table (CodeWalker, 20,300
  names) resolves 57 properties but only 4 of 234,720 `id1` values, so types are
  a third vocabulary. Three attempts (corpus, engine metadata, 40 engine class
  names) give 0 usable hits against 21 `root_type` + 21 `type_tag` values, so the
  names are probably not readable strings at all — likely stored in the encrypted
  LSNS. Do not retry with another dictionary.
- [ ] Rehash all of `levels`.

## Next

- [x] Re-index all 22 archives for `chain_start`; verified tiling 22/22 and the
  column is sound. The rule stays conservative by design: enabling the obvious
  padding fix merges every page archive into one chain (`shaders`: 4,205 pages
  in 1 chain), so grouping still needs a per-entry marker.
- [ ] Map the type/class IDs and transforms.
- [ ] Resolve the unnamed object roots.
- [ ] Packs active-learning queue.
- [ ] ACE1 trailer pairs.
- [ ] Locate compiled shader bytecode.
- [ ] Script object root field roles.

## Blocked

Each needs a specific input, not more effort.

- [x] ~~Directory/virtual rows in the entry count — needs Front B key material.~~
  Not blocked: the row shows up in the payload as one extra struct stream per
  pack. With `structs-1` as a model, `core_bvh4` verifies 1,227/1,261 packs
  (97 %), `levels` 784/2,044, `data` 21/40.
- [x] Mixed packs measured per pack: `tools/pack_model_fit.py` fits an exact
  model for 1,171/1,261 `core_bvh4` packs, 31/44 `shared_minigame000`, 14/28
  `navmeshes`, 16/40 `data`, but only 686/2,044 `levels` and 0/1 for
  `shaders`/`common`. Results in `handoff/pack-model-fit.tsv`.
  `tools/entry_model.py` now measures the model per archive: pairs fit
  `core_bvh4`/`levels`/`core_restofworld`; `shaders.rpf` is 3 chains of ~1,400
  pages and the page rule explains 100 % of continuations, so what is missing is
  the boundary between chains, not the continuation rule.
- [ ] Front B table `S` — same mask problem.
- [x] ~~9→10 byte stride boundary — needs a pack at N = 255 or 256.~~ Closed as
  mis-framed: `tools/frontb_stride.py` solves 3,029 headers and finds a 76-row
  pack already at 10 bytes while 254-row packs stay at 9, so count is not the
  discriminator. It depends on the row values themselves (offset width), which
  needs a decoded Front B, not another pack size.
- [ ] `+0x50` profiles as cipher parameters — needs a crib or key material.
- [ ] Front A milestone on `story000_bvh4.rpf` — needs independent table framing.
- [ ] Exact end of the last `data.rpf` child — needs an independent trailer start.
- [ ] Multi-mip texture tail — needs a multi-mip dictionary.
- [ ] The 331,728-byte `script.rpf` blob — needs a PC launch or a new sample.
- [ ] Full RPF9 metadata key recovery — needs key material or a second build.

## Health

- [x] `tools/check.sh` runs the analysis tests, the index invariants, the
  `rdna2-spirv` suite and the docs build in one go; all four pass today.

## Not mine

- [ ] `explorer/` — owned by another session.
