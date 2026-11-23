# Plan

Live check/todo list. Evidence, measurements and the failures that led here belong
in [investigation.md](investigation.md) and `handoff/`; completed work is one line
of state, not a log.

Last updated: 2026-11-23 (executable acquired).

## Current state

- **Corpus:** 22 archives indexed — 4,415,850 ranges / 161.3 GB stored / 365.0 GB
  decoded; every index tiles its archive. Source archives mirrored to local NVMe
  (`/home/lynxnathan/gta6-source`), verified by size/mtime on every path and by
  hash on a sample.
- **Entries:** one corpus pass (4 min, parallel) fits an entry model per pack and
  emits payload-derived manifests for 14 archives — **188,298 entries**, exact
  count verification (`--tolerance 0`). `core_bvh4` reproduces the declared count
  for 1,253 of 1,261 packs.
- **Audio:** complete — 93,344 Opus + 1,818 XMA2 + 73 ACE1 streams, 0 failures;
  `frames × channels / declared` never below 1.0.
- **Script schema:** `PSIN` parsed (62,910 typed rows; 25 of 301 properties and
  515 of 14,653 keys named). `LSNS` is a table container — 1,012/1,012 records
  parse, 58,697 sixteen-byte records.
- **Names:** one registry, 36,952 hash→name pairs with confidence and an
  ambiguity flag for JOAAT collisions; every handoff table annotated (4.3 % of
  hash values named corpus-wide, concentrated in bones and the script schema).
- **GPU:** shader decompilation is a separate repository, `rdna2-spirv/`.
- **Health:** `tools/check.sh` (tests, index invariants, shader suite, docs build).
- **Executable:** `game_scarlett_master.exe` obtained (sha256 `e95020b2…8993`,
  120,181,760 B, PE32+ x86-64, timestamp 2026-11-13). Authentic, not a launcher:
  `.xbld`/`.retplne`/`.voltbl` sections and imports of `d3d12_xs`, `xg_xs`,
  `xmem`, `xapu`, `AcpHal`, `XCRDAPI`, `XboxBvhBuilder`, `Bink2Scarlett`.
  Analysis harness: `tools/pe_audit.py`, Ghidra headless (`cache/ghidra/Target.java`,
  `-noanalysis`, 8 GB heap — 20 GB gets OOM-killed).

## Now

- [ ] Decide whether the RPF front region is **stored as-is** (a hash table) or
  decrypted above the archive layer. The full read→mount→entry-walk path
  (`0x140fc2540` → `0x141fb2600` → `0x1408ec210` → `0x1406bd160`) contains **no
  cipher call**, and the earlier "CBC" evidence was retracted — identical plaintext
  prefixes explain the predecessor statistic without a cipher.
- [ ] Decompile the second constructor (`0x1411a89c0`) fully, and follow
  `vtbl+0x3f8` / the `0xc26722d233648ae7` request into the file layer that supplies
  `[file+0x10]`, `[file+0x18]`, `[file+0x20]` — that layer is where a transform, if
  any, must live.
- [x] `LSNS` table structure: `[path of ≤10 × 128-bit levels][per-script records]`.
  The path nests — 853 tables share level 1, 381 share all ten, 120 share the full
  path — so it encodes a hierarchy of script kinds, not a flat type id. Records are
  not sorted in any interpretation.
- [ ] What the per-script `LSNS` records contain. Within a kind the tail length is
  fixed (22–23, 19–20, 20–21) while every tail differs, so they are per-script
  values; contents remain opaque 128-bit words, and no word matches a name or a
  PSIN key.
- [x] `PSIN` tree segmented: `tools/psin_segments.py` splits a record where the
  table period changes. The four clean records come out as one leaf each (width
  4×3, 6×1); record `1054` decomposes into widths 2/4/4/6/2 plus flat spans.
  371 table leaves and 5,015 flat over 849 records.
- [ ] What the widths mean (2 = an `Id`/`Type` pair list, 4 and 6 wider records).
- [ ] Name the remaining ped-rig bones and weight hashes. The 174k-token corpus
  sweep is exhausted (4 bone candidates, 1 weight candidate, both unverified);
  this needs a new vocabulary source, not a wider search.
- [ ] Entry model for `levels` (728 of 2,044 packs exact). The failures are
  systematic — about five non-entry struct streams and ninety surplus data
  streams per pack, i.e. entries owning several data streams. Needs the
  entry-type distribution.
- [x] Extraction browser rebuilds for every archive; a missing verification row is
  shown as "indexed only" instead of failing the build.

## Next

- [ ] ACE1 trailer pairs (15 u32 fields; 73 streams, all decoded).
- [ ] Map the script type/class IDs and transforms.
- [ ] Resolve the unnamed object roots.
- [ ] Packs active-learning queue.
- [ ] Script object root field roles.

## Blocked

Each needs a specific input, not more effort.

- [ ] RPF9 table of contents — content unidentified: `Front A`/`Front B` are
  uniform random, hold no known name hashes at any 4/8-byte field, and the reader
  does not decrypt them, so either they are the table as stored or the transform is
  above the archive layer. Every entry here is payload-derived.
- [ ] Cipher identity for the front region: not AES (forward S-box absent, the one
  inverse S-box is CNG library code), not CNG (no `BCryptEncrypt`/`Decrypt`
  imports), no Blowfish; ARX constants present (Murmur ×17, TEA delta ×11).
- [ ] Front A milestone on `story000_bvh4.rpf` — needs independent table framing.
- [ ] Exact end of the last `data.rpf` child — needs an independent trailer start.
- [ ] Multi-mip texture tail — needs a multi-mip dictionary.
- [ ] The 331,728-byte `script.rpf` blob — needs a PC launch or a new sample.
- [ ] Script bytecode itself: not in a plaintext section. The executable is now in
  hand, so this is a code-tracing task, not a waiting task.
- [ ] Type-name vocabulary (`root_type`, `type_tag`): three vocabularies return
  nothing usable; most likely stored as text inside the masked data.

## Not mine

- [ ] `explorer/` — owned by another session.
