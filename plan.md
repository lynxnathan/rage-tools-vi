# Plan

Last updated: 2026-11-21.

Roadmap, todo, and current state for the RPF9 extraction work. Detailed evidence
and narrative live in [investigation.md](investigation.md), which is an
append-only journal. Add new findings there and keep this file current.

## Workstreams

| Worktree | Branch | Role |
| --- | --- | --- |
| `main` | `main` | Integration, shared docs, extraction, analysis, merges |

The two investigation worktrees were archived and removed after consolidation;
only `main` remains. The historical script/data ownership notes are preserved in
the journal and `COLLAB.md`.

## Objective

Enumerate every archive entry, locate its stored bytes, and extract it with the
correct decoding.

**First delivery:** one general extraction workflow across the local RPF9
archives. Publish a manifest that distinguishes decoded payloads, preserved raw
ranges, and unresolved entries. Verify source coverage and extracted bytes.

Include a quadtree view of the extraction hierarchy. Show archives, packs, and
extracted files or ranges in nested quadrants with drill-down and back
navigation. Keep ranges with uncertain pack membership at archive level. The
view uses the extraction hierarchy and requires no spatial coordinates or links
between tiles.

Investigate individual models, movers, and skeletons after the general workflow
and view are usable. Archive index decoding remains relevant when it improves
entry identification, coverage, or decoding across the archive set.

## Current state

### Archive metadata

- RPF9 header is `0x60` bytes; Front A is `0x60..+0x08`, Front B is
  `+0x08..+0x04`, and the trailer is `end-+0x0c..end`.
- All three regions are 16-byte multiples. Front B is 32 bytes for N = 2 and
  48 bytes for N = 4, but large tables do not fit one record width.
- Trailer prefixes form two groups: four N = 2 scopes share 16 bytes, the two
  64-byte N = 2 trailers share 32, and the N = 4 pair shares a different 32.
- The trailer suffix is CBC-like: shared prefixes end on block boundaries and
  repeated blocks track their predecessor. No key or plaintext name recovered.
- `common.rpf`: 954 verified streams, 277 chains, 117 opaque spans, 394
  candidate groups against `+0x24 = 418`; 18 non-mount directory prefixes from
  recovered XML, so the 24-entry gap is not yet explained.
- The two `common.rpf` partial streams are damaged or multi-object spans, not a
  page/16-byte framing header.

### `data.rpf` and corpus extraction

- The local extraction is in `output/data.rpf/`. Each identified language
  has a folder named after its RPF, with offset-named UTF-8 text exports
  indexed by `localized/text.tsv`.
- The six top-level archives have 30,527 checksum-verified zlib streams.
  The extraction manifest covers every stored byte, including opaque spans
  and zero runs.
- `data.rpf` has 42 plausible headers including the root, 28,509 verified zlib
  streams, and 40 carved child-pack candidates. The child at `0x1a279000`
  still needs an independently supported end.
- Thirteen localization packs share identical 29,856-byte trailers. The
  translated payloads identify every language in the order declared by
  `core_language`. Each pack has 1,115 minimum-padding zlib groups.
- The child at `0x964000` contains 156 raw DEFLATE streams that yield 136
  credits pages and 20 credits configurations in RBF0.
- Of 2,281 PSIN-starting default chains, 2,256 validate as complete,
  including 56 that use PMAP/PSCH/PSIG layouts. The other 25 have
  structurally validated reconstructions from aligned zlib and raw segments.
- 1,260 default decoded chains begin with RBF0 and have readable root
  identifiers. They include UI prefabs, animation graphs, screens, and
  movie subtitle containers, plus the 156 separately extracted RBF0
  objects in the credits pack.
- The child at `0x1228e000` contains 2,502 distinct pointer-backed resource
  names, including 1,075 `.#dr` and 1,427 `.#ft` names for weapon models
  and components.

### Script pack at `script.rpf@0x1000`

- Two entries: a 42-stream object (2,702,384 bytes) and a 331,728-byte blob.
- Object: 30,683 records, 483 roots, 30,200 tagged references, 81 record sizes,
  136 `(size, pointer-layout)` struct groups.
- **306 of 483 roots** map to JOAAT names; 331 part/field names found. The object
  is a named vehicle model, part, and skeleton hierarchy.
- The `data.rpf` PSIN bone corpus contributes 3,212 plaintext part names. JOAAT
  matching finds 1,977 object-tree hits (expected 0.75), naming windows, doors,
  mirrors, seats, and wheels. It adds no root names.
- Named root group: 32-byte records with a tagged pointer at `+0x18`.
- Schema names in plaintext LSCH/PSIN: `x`, `y`, `z`, `datatype`, `name`,
  `flags`, `item`, `attributes`, `root`, `heading`.
- The blob has no detected tree index, no significant JOAAT name structure, and
  is parked until PC launch.
- Rotation transforms are decoded: named parts point to 32-byte leaves with type
  hash `0xfc86dde2` and a float angle in radians. `boot` includes -72 and -90
  degrees; `bonnet` includes 60 and 75 degrees.
- Large no-pointer records are typed arrays with a 48-byte header. The header
  stores used count at `+0x14`, stride at `+0x18`, and element type hash at
  `+0x28`; the body is `count × stride` with less than 16 bytes of alignment
  padding. The complete inventory finds 7,960 arrays with strides 4, 8, 12, 16,
  32, and 48. `0xc92cdeca` is the JOAAT of `vector3`; its 82 arrays hold three
  floats plus pad. No 3x4 or 4x4 matrix block has been confirmed.
- The 44 class-0 roots with point arrays each have one `0x5387a04e` bone table:
  `class-0 root -> 0x35e28de -> table -> 0x6503b274 bone node -> 0x1ebb416b
  point array`. There are 44 tables, 3,043 entries, and 3,043 point arrays.
  Each 16-byte table entry is a name hash plus a tagged pointer; table sizes
  range from 4 to 155 (102 for roots 0 and 209). The 612 table hashes are shared
  across roots and do not match JOAAT, CRC32, or common string hashes over 381k
  candidates. The flattened table is `handoff/script-bones.tsv`.
- Vehicle-like roots: **385** total, **306 named**, **244 with mover curves**.
  Artifact: `handoff/script-vehicles.tsv`.
- The `0xb066759f` arrays are **vehicle mover curves**: 1,935 curves under 244
  named vehicle roots, 36 channel keys, entry `[t,0,0,0,0,y,z,0]`. JOAAT names
  resolve the four window movers and two rear-door channels; four common
  channels remain unnamed. The y/z units are **unresolved**: the rigorous
  native-precision grid test matches the continuous baseline, so the earlier
  degree-quantization claim is retracted. The positional bonnet/boot
  interpretation is also withdrawn. Artifact:
  `handoff/script-vehicle-curves.tsv` and
  `handoff/script-vehicle-curve-quantization.tsv`.
- Class-0 roots form **16 near-identical skeleton families** at Jaccard >= 0.75;
  the data-side name match is negative (0/44 roots, 0/612 hashes).
  F01 has 12 roots (76–107 bones, 51 core hashes); F02 has 10 roots (40–66
  bones, 40 core hashes); F03 has 4 roots (116–134 bones, 101 core hashes).
  Exact-set grouping produces 38 groups, so the families expose optional bones.
  Artifacts: `handoff/script-bone-geometry.tsv`,
  `handoff/script-bone-templates.tsv`, and
  `handoff/script-bone-template-families.tsv`. Geometry hints: F02 is narrow
  and long (weapon-like candidate); F03/F04 are large (vehicle/trailer-like);
  F01 is medium and unresolved. These are heuristics, not names.
- The `0x1ebb416b` 48-byte-entry arrays are class-0 data: 3,043 arrays, 15,732
  entries, 44 roots of type `0xb0399a69`. Each entry has a vec3 at `+0x00`, a
  second vec3 at `+0x10`, a u32 at `+0x20`, and zero padding. Of 15,732 entries,
  10,895 have only the first vec3, 3,704 have both (a point/segment split), and
  1,133 are zero. The u32 is `[high:8][index:8]`, with index
  0..49 and high bytes 0, 1, and 2; 141 distinct IDs occur. In 2,208 arrays the
  same index has high-1 and high-2 entries (4,650 pairs), with distances from 0
  to 3.18. The pairing is not yet assigned to endpoints, layers, or sides.
- The `0x8f18aff0` arrays hold `(u32 hash, f32)` pairs: 2,491 arrays, 7,630
  entries, 252 distinct hashes. None matches the data bone corpus, XML/token
  dictionary, or resource-name dictionary. They sit under 25 roots of type
  `0xd72178e2` across classes 0, 1, 2, 3, 5, 6, and 8, not under the class-0
  bone-table roots. The `0xc92cdeca` vector3 arrays share that type-`0xd72178e2`
  family (38 roots). The `0xb066759f` arrays use a 32-byte stride;
  `0xb1ee00d0` uses 48 bytes with the vec3 at `+0x10`.
- The graph uses 48-byte property nodes with key and value pointers, plus arrays
  with 8-byte pointer entries or variable-stride value entries. The `+0x08` words are
  type/class IDs: all property nodes share `0xc4e5502a`, and key/part nodes use
  58 distinct IDs. They do not match the JOAAT dictionary or schema sections.
- The `+0x04` root word is `[u16 zero][u16 class]`. Class `0xffff` is
  vehicle-like (385 roots); class `0` has 86 roots; classes 1, 2, 3, 5, 6, and 8
  hold the other 12.
- Child type IDs are disjoint by class: vehicles use `0xc8eaca7f`, class 0 uses
  `0x35e28de`/`0xee8f65ba`/`0x5b8ff882` and smaller groups, and the other classes
  mostly use `0xee8f65ba`.
- Front A tables after `0x160` are 16-byte multiples but share no bytes across
  controls; all 171 aligned blocks are unique. The `0x160` table boundary is not
  confirmed by a common prefix.
- The large localization mode (`0x00020007` / `0x00090f02`) has Front B =
  `align16(12 × (N+1))` in all 14 headers. N = 1,168 and script_large N = 1,012
  disambiguate this from 12N. Small modes do not follow 12N.
- Both discriminating counts are N mod 4 = 0, so an extra 12-byte row, a
  16-byte pad, and a header/sentinel rule coincide. A same-mode N mod 4 = 1 or 2
  sample is needed; none exists in the current cohort.
- Across american, brazilian, and german, Front A and B share no prefix, suffix,
  or aligned 16-byte block; byte equality is at chance. The cipher and field
  placement remain open.
- The 10N residual closes the size table: story, core, appdata0, script root,
  script small, and data root fit `align16(10N)`; the large localization mode
  fits 12N/12(N+1) instead. The 13 localization packs share N = 1,115, so that
  is a cohort observation, not a cross-N law.
- Metadata size inference is closed. No further blind byte scans; indexed
  extraction is parked pending independent framing, key material, or a decoded
  field.
- The `+0x10` wrapper probe finds 12,332 wrappers, 7,960 direct leaf targets,
  and zero direct rotation leaves. Raw `+0x08` splits the population into
  `0x6503b274` (3,043), `0xb24165eb` (2,491), `0x114ce194` (1,935), and smaller
  families; `0xc8eaca7f` is the 46-record vehicle-root forwarder with 44 named
  parents.
- The `+0x18` test has 3,540 records (305 roots, 1,953 parts, 1,282 unnamed),
  1,230 direct leaf targets, and all 1,230 are rotations; there are zero
  negative leaves. Non-leaf target words are `0xa03e7c22` (1,935) and
  `0xc8eaca7f` (375). The leaf tag is the only reliable discriminator; the
  parent-field test is degenerate. Angles vary by part: boot/bonnet are
  vehicle-specific, doors are mostly 0, window winders are mostly -2π.
- No independent named-vehicle → class-0 layout link was found. Common XML has
  0 `<layout>` tags in 259 files, decoded data has 0 model-layout metadata, and
  27 external model/layout pairs (17 layouts, 108 JOAAT variants) match 0 of 86
  class-0 roots and 0 of 483 roots. The shared bone list is supportive only.
- Native texture extraction expanded from 4 controls to 73 valid dictionaries:
  788 textures, 306,008,064 bytes, manifest at
  `output/data.rpf/textures-expanded/manifest.tsv`. Dimensions, format codes,
  hashes, strides, pointers, and bounds validate.
- The shader marker scan is negative: no DXBC, DXIL, SPIR-V magic, DDS, GNF, or
  KTX in the decoded corpus. The seven grep hits were localization text
  (`PLMDDS`, `SUSPIRO`) or binary-regex false positives. SPS1 provides names
  only; no compiled shader is verified.
- Top-mip decode trial: `loading_screen_spinner_i1` (32×32, format 0x4D) has a
  plausible BC3 candidate at offset `0x800` with 4×4-block tiles. The
  `hud_i8d6`/`hud_i689` holdouts do not render coherently under offsets
  0/0x2000/0x4000/0x6000 and tiles 1/2/4/8. Descriptor bounds agree; top-mip
  offset, mip order, pitch, tile order, and codec remain unknown.

### Script sections

- PSIN, LSCH, LENM, and LRSC are plaintext.
- LSNS is the only chained-encrypted section. It has a 12-byte `(1, 257,
  block_bytes)` header, all repeated blocks share a predecessor, and 853 first
  blocks repeat. CBC-like with a build-wide key and fixed/deterministic
  chaining value.

## Working loop

1. Append evidence to `investigation.md`; never rewrite old entries.
2. Update the current state and todo in this file.
3. Update the UML/model pages in `docs/` when the model changes.
4. Build the living docs (`tools/docs.sh build`) and commit code + docs together.
5. Keep `site/`, `.venv-docs/`, `*.rpf`, and `output/` untracked.

## Extraction first

- Downloads corpus: 14 extracted archives and a selective stream index for
  `anim.rpf`. The index was checked against the source and is available in
  `output/downloads-corpus/index.html`. Seven large archives remain to index.
  Process `packs.rpf`, `navmeshes.rpf`, `core_bvh4.rpf`, `movies.rpf`,
  `story000.rpf`, `audio.rpf`, then `levels.rpf` in ascending stored size.
- Normalized inventory covers all eight local archives: **86,029 ranges /
  1,096,854,128 stored / 1,896,307,661 decoded**. Unclassified: 429,764,784
  bytes, dominated by shaders (273,959,915) and textures (136,021,963).
  `full` means range coverage, not authoritative entry names.
- General entry point: `tools/extract_entry.py` wraps the Rust extractors and
  logs sha256/byte counts. Six-case matrix passes: script object/blob, data
  zlib/unclassified, common zlib, story zlib.
- Archive containment view: `tools/extraction_tree.py` builds
  `output/general-extraction/index.html` from the verified manifests. The
  optional resource-local XY view remains under `output/script-quadtree/`.
- Unclassified triage: 6,111 spans / 429,764,784 bytes; shaders 273.96 MB,
  textures 136.02 MB, data 19.13 MB, script 431,696 B (parked blob), common
  210,272 B, appdata 5,216 B, core 4,976 B. Artifacts:
  `handoff/unclassified-summary.tsv`, `handoff/unclassified-gaps.md`.
- Still missing: authoritative entry names/semantics for those unclassified
  bytes; the range layer is complete.

## Audio (Xbox AWC)

- `audio.rpf` contains `ADAT` AWC containers inside a large unclassified span.
- Extracted **6,625 AWC containers / 23,510,392,992 bytes** with SHA-256;
  local report `handoff/audio-awc.md`, tool `tools/extract_awc.py`.
- Header: version 1, flags `0xff21`, 6–24 streams, chunks `0x55` data /
  `0x36` peak / `0xA3` seektable / `0x76` format.
- `0x76` is a 32-byte descriptor: sample counts at `+0x00`/`+0x0c`, rate at
  `+0x08`, codec at `+0x1c`, sub-ID at `+0x1d`. Corpus scan: 2,320 parsed streams;
  codec `0x0b` 2,081 / `0x05` 166 / `0x02` 73; rates 48k, 32k, 12k, 28k.
- Data chunks are multiples of 2,048. Many begin `a0 00 f8` and repeat it at
  offset **162** (1,451 rows): a real internal framing signal.
- **Codec `0x05` = XMA2: solved.** The first wrapper used `wFormatTag=0x0161`
  (WMAudio2); the correct tag is `0x0166`. `tools/extract_awc_xma2.py` decoded
  151/166 streams to 86 MB of WAV; all 151 non-silent, 148 tonal. First
  non-zlib codec family decoded from `audio.rpf`.
- `0x0B` remains Bink Audio 2 hypothesis; `0x02` unresolved. Next: split `0x0B`
  at the `a0 00 f8`/162 marker; if silent, test AWC/XXTEA encryption/key source.

## Large archive pilot

- `anim.rpf` read-only index: 4,407,626,384 bytes, 259,138 spans, 130,509 zlib,
  11,572,883,428 decoded, 37,742,843 unclassified. Rust `map` used 4.34 GB RSS
  and 3m49s.
- Bounded selective extraction via `tools/mmap_extract.py`: 2,808 bytes at
  `0x6000..0x62dc`, 15 MB RSS, same sha256 as Rust.
- Streaming index completed all eight remaining archives: 157,764,783,840
  stored / 2,190,635 zlib / 360,572,388,767 decoded / 26,072 unclassified.
  Indexes total 184 MB under `output/downloads-corpus/index/`. Peak RSS 15.91 GB
  (audio), 8.16 GB (story000), 8.11 GB (movies); levels 1.21 GB.
- The Rust 16 MiB `MAX_PAYLOAD_SIZE` would lose **96 streams**. Tested stream
  `0xed61e010..0xee4ff55f` (20,578,304 bytes): mmap extracts with sha256
  `e9600e6f…c7c9`; Rust fails at the start.

## Full output rebuild (2026-11-21)

- `output/` was deleted and rebuilt from the external source tree; the canonical
  export command is `tools/export_all.sh SOURCE_ROOT OUTPUT_ROOT`.
- Indexed all 8 large archives: **2,190,635 zlib streams / 360,572,388,767
  decoded bytes**. `levels` and `movies` are index-only; `levels` alone decodes
  to 174.9 GB.
- Extracted and SHA-verified six archives: `anim` 130,510 / 11.59 GB;
  `packs` 144,366 / 9.74 GB; `navmeshes` 90,305 / 20.55 GB; `core_bvh4`
  565,596 / 129.93 GB; `story000` 141,163 / 13.77 GB; `audio` 838 / 54.1 MB.
  All 6/6 verification rows PASS (missing 0, extra 0, failures 0).
- Rebuilt `audio.rpf` AWC/XMA2 with `tools/rebuild_audio.sh`: 6,625 AWC
  containers / 23.51 GB and 151 XMA2 WAVs / 86 MB.
- Current output is ~209 GB; local disk has ~100 GB free. Move to the external
  volume before extracting `levels`.

## Bulk extraction

- `tools/bulk_extract.py`: parallel zlib span extraction, one sharded file per
  stream, manifest with sha256.
- common test: 954 streams / 50,231,123 bytes / 0.11s.
- packs full: 144,366 streams / 9,735,393,283 decoded / 16 workers / 577s /
  5.33 GB RSS; output on Mammoth. Manifest matches index. `tools/verify_bulk.py`
  result: 144,366/144,366, missing 0, extra 0, failures 0 (PASS).
- Data owns navmeshes/core_bvh4/movies/story000/audio/levels full extraction;
  script owns packs.

## Packs signature survey

- Post-extraction classification of 144,366 packs streams: binary 113,480
  (4.25 GB), `u16_4042` 28,713 (5.43 GB), `0f000080` 1,148, PSIN 586, XML 386,
  zero 47, zlib 5, RBF0 1. `u16_4042` probe: 2,992 sizes, 64 KiB-multiple
  classes, small header words ending 0x21/26/28/25, not offsets; low byte likely
  a type tag. Size classes split into metadata-like 1,040/256, high-entropy
  393,216/851,968/524,288, and structured 131,072/196,608/262,144/65,536.
  `0f000080`: 1,148 streams / 11.69 MB, ~10 KiB each, entropy ~6.9,
  full-range 16-bit payload; likely quantized geometry/navmesh or animation.
  Dominant resource headers still unnamed.
- ML clustering pilot: 113,480 binary streams / 32 clusters. Largest families
  are zero-prefixed `...0050` tables; visible subgroups include `GM_U01_C`,
  `0x4040`, `0e000080`, float-like headers. Proposal engine only.
- Next: active-learning queue of representative/uncertain samples for the operator's
  labels; after labels, train a small supervised classifier and keep the
  deterministic verifier as ground truth.

## Semantic logs

- `handoff/packs-semantic-log.md` is the consolidated packs extraction/probe log,
  including signature counts, `u16_4042` size regimes, `0f000080` probe, tools,
  and commits.

## Worktree consolidation

- `investigate/script-graph` is archived externally and its worktree was removed; its content is integrated in `main`.
- `investigate/data-rpf` is archived externally; the worktree
  `DATA_WORKTREE` was tarred to
  `ARCHIVE/data-worktree-20261120T203324.tar.gz`
  (970M; sha256 `cb2a87c9…e25e9`) and removed. Branch deleted. The archive
  checksum file was removed from the clean repo.
- Only `main` remains in `git worktree list`; temporary test artifacts were
  cleaned. Source, indexes, and verified extraction outputs were retained.

## Dual protocol

- `#0054` (restore direct inotify) is closed by `17cc1c2`.
- `#0067` closed when `data` sent `#0071`. The JOAAT comparison found no matches
  for the 44 roots or 612 bone hashes in the tested name corpora. Verified
  model, layout, and bone-order mapping remains open research.
- Both sessions use the `main` copy of `tools/bus.py` for direct inotify standby.

## Documentation

- `mkdocs.yml` builds a Material site from `docs/`.
- Mermaid UML is rendered through `pymdownx.superfences` + Mermaid v11.
- Root documents (`plan.md`, `investigation.md`, `format.md`, `AGENTS.md`,
  `COLLAB.md`, `pi-payload-audit.md`, script journal/status) are included at
  build time, so the site is a projection rather than a second copy.
- `tools/docs.sh serve` runs the live site; `tools/docs.sh build` writes `site/`.
- `.github/workflows/docs.yml` builds the site on push/PR.

## Roadmap

### Now

- [ ] **Front A milestone on `story000_bvh4.rpf`.** The N = 4 pack has four
  exact XML ranges. Plain known values and the post-`0x160` table comparison both
  fail to expose a plaintext record. The metadata size handoff is parked; the
  next test needs independent framing, key material, or a decoded field.
- [x] **Bone geometry classification.** Exported per-bone centroids/extents and
  clustered the roots into 16 skeleton families.
- [ ] **Name the skeleton families.** Validate the bone hash namespace and order
  with an independently decoded model skeleton. Use geometry to prioritize
  vehicle, ped, weapon, and prop candidates.
- [x] **Close the four-channel test.** Same-root join and grid/leaf
  discriminators are negative; names and units stay open. Reopen only with a
  decoded `0xb066759f` schema or a named mover with a verified path/angle.
- [x] **Decode the remaining `0xb1ee00d0` variant.** 186 arrays / 4 class-0
  roots / 294 entries; sibling 48-byte layout with vec3 at `+0x10`; names open.
- [x] **Decode `0x8f18aff0`.** 2,491 arrays / 7,630 pairs; every array sums to
  1.0; normalized weight vectors keyed by 252 hashes.
- [ ] **Next: name the weight hashes.** Resolve the 57 shared bone hashes and
  the 195 other hashes, then join weights to vertices/parts. Parked behind the
  extraction-first priority.
- [ ] **Class, wrapper, and transform mapping (active enrichment).** The `+0x10`
  wrapper test is complete, and the `+0x18` test is complete: 1,230 of 1,230 leaf
  targets are rotations, with zero negative leaves; the leaf tag is the only
  reliable discriminator. The named-vehicle → class-0 layout link is negative.
  The generic array header is decoded, including the `vector3` type hash and the
  class-0 48-byte entries. The class-0 bone-table hierarchy and its 3,043 bones
  are flattened to `handoff/script-bones.tsv`. Next: identify the 612 table-hash
  names or hash algorithm, name the `0x8f18aff0` pair namespace, and decide
  whether the high-1/high-2 pairs are endpoints, layers, or sides.

### Next

- [ ] **Map the type/class IDs and transforms.** Group the property/key IDs by
  parent/child shape, use the bone corpus to name part records, and decode the
  value entries and packed transform representation.
- [ ] **Resolve the 177 unnamed roots.** 79 are vehicle-like; 86 are class-0
  layouts; 12 have classes 1, 2, 3, 5, 6, or 8. Import the data.rpf
  model↔bone-list or `vehiclelayouts` mapping when the other workstream exposes
  it.
- [ ] **Finish the `data.rpf` boundary work.** Resolve the final child end and
  the opaque streams near `0x120d7000` and `0x1a279000`; compare per-language
  fronts against the shared localization trailers.
- [ ] **Reconcile `common.rpf` 394 candidate groups with `+0x24 = 418`.** Decode
  one directory node to confirm the directory hypothesis.
- [ ] **Verify any proposed entry record** against exact stored ranges and files
  split across multiple zlib streams.
- [ ] **Use recovered names, offsets, or plaintext hashes** as cribs for Front A
  and the trailer.

### Parked

- [ ] The 331,728-byte blob and its seven-byte periodic islands. Revisit after a
  PC launch or a new sample; it does not block the forest or `common.rpf` work.
- [ ] Full RPF9 metadata key recovery; needs key material or a second build.

## Done

- [x] Map `common.rpf` stored ranges and payload groups.
- [x] Verify the 42-stream object, PSIN records, XML documents, and story control.
- [x] Confirm the three metadata-region sizes and header-word invariants.
- [x] Test trailer stream-vs-CBC behavior and full header diffs.
- [x] Separate encrypted LSNS from plaintext PSIN/LSCH/LENM/LRSC.
- [x] Resolve the continuation rule for 64 KiB zlib chunks.
- [x] Discover JOAAT naming and name 306 of 483 object-tree roots.
- [x] Partition the object forest into 136 struct groups.
- [x] Decode the typed array header and flatten the 3,043 class-0 bones.
- [x] Publish a living MkDocs Material + Mermaid site for the whole project.
- [x] Deliver the first extraction milestone: inventory, entry point, bone
  quadtree, containment viewer, and six-case verification.
- [x] Cluster the 44 class-0 roots into 16 near-identical skeleton families.
- [x] Decode 1,935 vehicle mover curves and name six JOAAT channels.
- [x] Inventory 385 vehicle-like roots and 244 curve-bearing vehicles.
- [x] Recover schema field names including `x`, `y`, `z`, `datatype`, `name`,
  `flags`, and `item`.
- [x] Decode part rotation leaves and confirm radians.
- [x] Identify the array container layout in no-pointer records.
- [x] Identify the property/key/value graph pattern.
- [x] Classify roots by header shape; isolate 79 unnamed vehicle-like roots.
- [x] Identify the `flags=0` linked-list class and its type-hash groups.
- [x] Decode class-0 layouts: 102-entry bone lists with 48-byte positions.
- [x] Import the data.rpf bone corpus and name 1,977 object-tree part fields.
- [x] Decode the `+0x04` u16 class split and partition child type IDs.
- [x] Compare Front A tables; no shared encrypted prefix after `0x160`.
- [x] Measure the large-mode Front B size relation and the A/B equality matrix.
- [x] Close the Front B size-mode handoff with 10N, 12N, and 12(N+1) residuals.
- [x] Probe `+0x10` wrappers: zero direct rotations; 1,230 controls under `+0x18`.
- [x] Test `+0x18` parts: all 1,230 leaf targets are rotations; no negative leaf control.
- [x] Test named-vehicle → class-0 layout references: negative across XML, decoded data, and external metadata.
- [x] Expand native texture extraction to 73 dictionaries and 788 verified textures.
- [x] Scan for compiled shader markers; none found in the decoded corpus.
- [x] Test top-mip linear/tiled layouts on one small texture and two holdouts; no two-sample conversion verified.

## Tools

| Tool | Purpose |
| --- | --- |
| `tools/extract_archive_ranges.py` | Extract all mapped ranges and verify source and output hashes |
| `tools/decode_raw_deflate.py` | Find and extract raw DEFLATE, including packed RBF0 objects |
| `tools/data_rpf_inventory.py` | Audit nested ranges, localization, credits, mixed PSIN records, and resource names |
| `tools/export_localized_text.py` | Export readable UTF-8 string runs from the language resources |
| `tools/scan_libmagic.py` | Inventory file signatures across a local extraction |
| `tools/audit_opaque_streams.py` | Check weak DOS labels, verify zlib candidates, and reconstruct mixed PSIN objects |
| `tools/identify_opaque_context.py` | Identify neighboring object headers, PSIN layouts, and RBF0 root types |
| `tools/metadata_regions.py` | Region sizes, header words, trailer prefixes, Front A split, directory inventory |
| `tools/section_blocks.py` | 16-byte block repetition across PSIN sections |
| `tools/script_pair.py` | Object/blob sizes, index searches, periodicity, blob name scan |
| `tools/root_names.py` | Match root IDs to JOAAT names |
| `tools/object_names.py` | Scan the object for name fields and show named subtrees |
| `tools/struct_types.py` | Partition records by size and tagged-pointer layout |
| `tools/schema_names.py` | Match JOAAT field names in LSCH/PSIN |
| `tools/transform_values.py` | Follow named parts to rotation/value leaves |
| `tools/array_records.py` | Detect header plus 16-byte entry arrays |
| `tools/array_types.py` | Decode generic array count, stride, and type tags |
| `tools/array_inventory.py` | Export every typed array with root context |
| `tools/pair_arrays.py` | Export 0x8f18aff0 normalized-weight pairs |
| `tools/extraction_inventory.py` | Normalize extraction manifests into one inventory |
| `tools/extract_entry.py` | General archive/range extraction entry point |
| `tools/extract_awc.py` | Scan/extract ADAT AWC containers from raw audio spans |
| `tools/awc_framing.py` | Inventory AWC `0x76` descriptors, data sizes, and frame markers |
| `tools/bruteforce_ueba.py` | Sweep AWC payloads through a synthetic UEBA/Bink Audio wrapper |
| `tools/test_awc_xma2.py` | Build XMA2 WAVE wrappers from AWC data chunks and decode |
| `tools/extract_awc_xma2.py` | Decode codec-`0x05` AWC streams to PCM WAV with manifest |
| `tools/rebuild_audio.sh` | Rebuild audio.rpf AWC/XMA2 output from the source archive |
| `tools/export_all.sh` | Rebuild all large-archive indexes/extractions and verify them |
| `tools/quadtree.py` | Build resource-local quadtrees and an HTML view |
| `tools/verify_quadtree.py` | Verify quadtree completeness and structural invariants |
| `tools/mmap_extract.py` | Bounded-memory selective zlib extraction |
| `tools/stream_index.py` | Streaming mmap range index with periodic madvise |
| `tools/bulk_extract.py` | Parallel full extraction from range indexes |
| `tools/type_tags.py` | Match array type tags against JOAAT type names |
| `tools/value_entries.py` | Classify 16-byte value entries |
| `tools/value_array_context.py` | Link typed arrays to root class and type |
| `tools/transform_pairs.py` | Test high-1/high-2 pairing in 48-byte entries |
| `tools/bone_table.py` | Flatten the class-0 bone table and point arrays |
| `tools/bone_geometry.py` | Compute per-bone centroids, extents, and shared hashes |
| `tools/bone_templates.py` | Group roots by exact bone-hash sets |
| `tools/bone_template_families.py` | Cluster roots into near-identical skeleton families |
| `tools/vehicle_curves.py` | Decode vehicle mover curves and JOAAT channels |
| `tools/vehicle_curve_quantization.py` | Native-precision grid test and leaf permutation baseline |
| `tools/vehicle_roots.py` | Inventory named vehicle roots and curve coverage |
| `tools/vehicle_bone_names.txt` | Public vehicle bone-name dictionary for channel matching |
| `tools/docs.sh` | Install, serve, or build the living MkDocs site |
| `tools/bone_corpus.py` | Match data.rpf PSIN bone names to the script tree |
| `tools/bone_names.txt` | 3,212 harvested bone/part names |
| `tools/property_tree.py` | Dump a named property/array subtree |
| `tools/root_classes.py` | Split roots by header shape and child signature |
| `tools/front_a_compare.py` | Compare Front A tables across the controls |
| `tools/localized_extents.py` | Compare localization ordinals and plaintext extent fields |
| `tools/front_ab_matrix.py` | A/B prefix, suffix, and aligned-block equality matrix |
| `tools/front_b_modes.py` | Front B size versus 12N and 12(N+1), grouped by header mode |
| `tools/wrapper_probe.py` | Tabulate +0x10 wrappers, parents, targets, and rotation controls |
| `tools/rotation_parts.py` | Tabulate +0x18 parts, leaf tags, angles, and repeated part families |
| `tools/layout_link_probe.py` | Test model/layout pairs against class-0 layout roots |
| `tools/native_texture_scan.py` | Scan decoded resources for texture dictionaries and export native textures |
| `tools/texture_decode.py` | Decode BC1/BC3 top-mip candidates and write PNG samples |
| `tools/pi_archive_audit.py` | Raw DEFLATE, root-ID, motif, and path probes |
| `tools/audit_payload_objects.py` | Independent payload-object audit |

## Open questions

- What cipher and key protect Front A and the trailer?
- Does the `common.rpf` count include directory nodes, and how many?
- Which 177 object roots remain unnamed, and which asset classes do they cover?
- Are the 32-byte root fields `name`, flags, hash, heading, and pointer, and
  where are the transforms stored?
- Is the 331,728-byte blob bytecode, compressed data, or an unrelated resource?
- Where is the compiled shader bytecode, if it is present in this corpus?
- What are the actual codec, top-mip offset, mip order, pitch, and tile order for
  format 0x4D and 0x62 textures?
- What do AWC codec IDs `0x0b` and `0x02` map to, and is the `a0 00 f8`/162
  marker a packet boundary or frame header? (`0x05` is XMA2.)
- Is the AWC `0x55` payload encrypted (AWC/XXTEA), and where is the GTA VI key?
- What hash produces the 612 class-0 bone-table names, and what are their names?
- What do the `0x1ebb416b` index/high-byte IDs and `0x8f18aff0` hashes name?
- Do the high-1/high-2 pairs in the 48-byte entries encode endpoints, layers,
  or two sides?
