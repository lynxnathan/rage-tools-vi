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

- [ ] Resolve the PSIN class (301) and field (14,653) hashes. Record layout is
  done and `tools/psin_property_tree.py --dump cache/psin-properties.tsv` gives
  all 62,910 rows; JOAAT-64/FNV-64/Murmur64 variants all miss, so the vocabulary
  needs the executable or the decrypted LSNS.
- [ ] Script decomp pipeline is gated on key material. Section split and PSIN
  directory are done; PSIN blocks are typed tables (22–38 % invalid opcodes vs
  49 % random), and LSNS is genuinely encrypted (uniform entropy, deterministic,
  no weak structure, no cipher tables in the shipped binaries). Reopen when a key
  or a second sample appears; the crib is the content-dependent first block.

- [ ] Name the remaining ped-rig bone hashes (99 of 282 done).
- [ ] Name the remaining weight hashes (21 of 252 done).
- [ ] Open the 330-hash universe with a new vocabulary source.
- [ ] Rehash all of `levels`.

## Next

- [ ] Re-index the eight large archives for `chain_start`.
- [ ] Map the type/class IDs and transforms.
- [ ] Resolve the unnamed object roots.
- [ ] Packs active-learning queue.
- [ ] ACE1 trailer pairs.
- [ ] Locate compiled shader bytecode.
- [ ] Script object root field roles.

## Blocked

Each needs a specific input, not more effort.

- [ ] Directory/virtual rows in the entry count — needs Front B key material.
- [ ] Multi-chain entry grouping inside mixed packs — needs a per-entry marker.
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

## rdna2-spirv (adjacent workstream)

- [ ] M0 decode tables: generate GFX10.x tables from AMD's MIT machine-readable
  ISA XML, decode SOP/VOP/SMEM sample, match `llvm-mc` on 100 random
  instructions. See `rdna2-spirv/PLAN.md`.
- [ ] Keep the tool generic: input is a byte range plus `--mcpu`; game or
  console containers stay optional adapters, never the core, and no proprietary
  or NDA material may become a dependency or an acceptance criterion.
