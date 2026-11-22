# Plan

Current state and open work. Narrative, measurements and evidence belong in
[investigation.md](investigation.md) and `handoff/`. Completed work stays as one
line of state, not as a log.

Last updated: 2026-11-21.

## Current state

- **Extraction:** all 22 source archives indexed; every indexed stream extracted
  with a hashed manifest. `levels` (174.9 GB) verified by completeness pass plus
  a 1,500-file hash sample. `movies` is the only index-only root (no zlib
  payload).
- **Entry level:** `core_bvh4` has a payload-derived entry manifest
  (`handoff/core-bvh4-entries.tsv`) with 1,214 of 1,282 packs matching the
  declared count exactly, and a full descriptor inventory
  (`handoff/core-bvh4-descriptors.tsv`).
- **Pack extents:** zero-padding boundaries proven on every archive tested; leaf
  extents published in `handoff/pack-extents-leaves.tsv`; parents remain open.
- **Metadata:** header census complete (`handoff/header-census-full.tsv`), Front
  A/B/trailer masked, size laws characterised. Metadata decoding is
  information-blocked.
- **Skeleton families:** the 16 clusters now carry readings — F12 is a hand rig
  (the decoded one), F13 a genital rig, F03/F04/F09 large animals; the unnamed
  families are the small-prop population and hold the 330-hash universe.
- **Naming:** bone-table and weight hashes share one namespace, JOAAT of
  `skel_`/`mh_`/`rb_` names: 99 of 612 table hashes and 21 of 252 weight hashes
  resolved, one rig fully decoded (`handoff/script-skeleton-0x48dcbb01.tsv`).
  A second, disjoint 330-hash universe remains unnamed.
- **Browser:** `output/extraction-index-pilot/index.html` rebuilt with seven
  verified archives.
- **Tooling:** `tools/pipeline.py` runs index → extract → audio → pilot → verify;
  exploration caches live in the untracked `cache/` on the NVMe.

## Now

- [ ] Cover `shared_minigame000_bvh4` with the same descriptor harvest.
- [ ] Name the remaining weight hashes (21 of 252 done).
- [ ] Name the remaining ped-rig bone hashes.
- [ ] Open the unnamed hash universe with a new name source.
- [ ] Repoint `tools/extraction_inventory.py` at the manifests.
- [ ] Rehash all of `levels`.

## Next

- [ ] Re-index the eight large archives for `chain_start`.
- [ ] Map the type/class IDs and transforms.
- [ ] Resolve the unnamed object roots.
- [ ] Name the unclassified payload bytes.
- [ ] Packs active-learning queue.
- [ ] ACE1 trailer pairs.
- [ ] Locate compiled shader bytecode.
- [ ] Script object root field roles.
- [ ] Verify any proposed entry record against exact ranges.

## Blocked

Each needs a specific input, not more effort.

- [ ] Directory/virtual rows in the entry count — needs Front B key material.
- [ ] Multi-chain entry grouping — needs a decoded per-entry marker.
- [ ] Front B table `S` — same mask problem.
- [ ] 9→10 byte stride boundary — needs a pack at N = 255 or 256.
- [ ] `+0x50` profiles as cipher parameters — needs a crib or key material.
- [ ] Front A milestone on `story000_bvh4.rpf` — needs independent table framing.
- [ ] Exact end of the last `data.rpf` child — needs an independent trailer start.
- [ ] Multi-mip texture tail — needs a multi-mip dictionary.
- [ ] The 331,728-byte `script.rpf` blob — needs a PC launch or a new sample.
- [ ] Full RPF9 metadata key recovery — needs key material or a second build.

## Not mine

- [ ] `explorer/` — owned by another session.
