# Rage Tools VI

RPF9 archive extraction, payload reconstruction, and object-graph analysis for
**GTA VI / Leonida** — built as an evidence problem, not a guessing game.

> **Goal:** enumerate every archive entry, locate its stored bytes, and extract it
> with the correct decoding.

## The idea in three lines

RPF9 archives hide their table of contents behind masked metadata (Front A,
Front B, the trailer), so this project reconstructs entries from the **payload**
and uses the masked table only as a cross-check:

- every payload range is found by scanning and **verified by zlib checksum**;
- every pack declares an entry count `N`, and Front B's size law
  (`align16(stride × N)`) turns that count into an oracle;
- every identifier met so far is **`JOAAT(lowercase name)`**, so names are
  recoverable by vocabulary instead of by key.

Full walkthrough: **[From first principles](docs/explained.md)**.

## Highlights

| Area | Result |
| --- | --- |
| Corpus index | **22 archives · 4,415,850 ranges · 161.3 GB stored · 365.0 GB decoded** — every index tiles its archive exactly |
| Bulk extraction | **2,190,635** zlib ranges extracted and SHA-256 verified |
| Entry manifests | **328,481 entries** with exact boundaries across 4 archives, self-consistency PASS |
| `core_bvh4` descriptors | **269,106** rows: exact payload size, orthonormal basis (269,105/269,106 within 1e-3) |
| Unclassified layer | **closed** — 38.1 GB audio, 13.4 GB video, no unnamed game payload |
| Cutscene audio | **196,350 Opus streams / 148.3 hours** decoded from a second AWC variant |
| Naming | **99 / 612** bone-table hashes and **21 / 252** weight hashes resolved via `skel_`/`mh_`/`rb_` |
| Decoded rig | root `0x48dcbb01`, **34 / 34 bones** — a two-sided hand rig |
| Browser | static extraction browser over seven verified archives |

## What is solved, and what is not

**Solved.** Payload coverage and verification; entry boundaries for four
archives; the `core_bvh4` descriptor format; three AWC audio container variants;
the JOAAT naming convention for rigs; the media composition of the "unknown"
bytes.

**Open.** The masked metadata itself (Front A, Front B, trailer) — four questions
are information-blocked on key material or a crib. 330 bone hashes belong to a
namespace whose vocabulary is unknown. Packs whose entries mix shapes cannot be
counted exactly and are marked rather than guessed.

The live list is [`plan.md`](plan.md); the raw evidence is
[`investigation.md`](investigation.md).

## Using the names

Every resolved hash across the repository — bones, weights, script properties and
object keys — is merged into one registry, so other tools can join against it
instead of reading six files with six schemas.

```bash
# rebuild the registry from every name table
python3 tools/name_registry.py --build

# what is this hash?
python3 tools/name_registry.py --lookup 0x01166164 0x67d26872 0xf5436868

# add name / name_kind / name_confidence columns to any TSV with a hash column
python3 tools/name_registry.py --annotate handoff/script-bones.tsv \
    --column bone_hash --out handoff/script-bones-named.tsv

# read a script's schema instead of 62,910 lines of hex
python3 tools/psin_dump.py --record 110
python3 tools/psin_dump.py --property position
```

The registry also carries the engine's own metadata names (20,300 of them, from
CodeWalker's public `MetaNames` table) as a `meta` confidence level above
`corpus`:

```bash
python3 tools/fetch_vocab.py     # downloads it into cache/vocab/ (untracked)
python3 tools/name_registry.py --build
```

261 of the 267 hashes named by both that table and our corpus sweep agree
(98 %). Where two real strings share a 32-bit JOAAT the row is marked
`ambiguous` and `--lookup` says so, rather than picking one.

To annotate every handoff table at once (hash columns are detected by their
values, not their names):

```bash
python3 tools/annotate_handoff.py       # writes output/named/ and handoff/name-coverage.tsv
```

`handoff/name-coverage.tsv` says, per table, how many hash values now carry a
name — 31,896 of 746,679 (4.27 %) at present, concentrated in the bone, rig and
script-schema tables. Annotated copies are derivable and stay untracked in
`output/named/`.

`handoff/names.tsv` is `hash, name, kind, confidence, source, also_known_as`.
Confidence is ordered `curated > grammar > corpus > candidate`, and a hash that
two sources disagree about keeps the losing name in `also_known_as` rather than
dropping it.

## Documentation

The site is built with MkDocs Material + Mermaid:

```bash
tools/docs.sh build     # writes site/
tools/docs.sh serve     # live preview
```

Start with [From first principles](docs/explained.md), then
[What we found](docs/findings.md). Deeper pages: [RPF9 format](docs/rpf9/format.md),
[Metadata regions](docs/rpf9/metadata.md), [Entry manifests](docs/extraction/entries.md),
[Rig names](docs/data/rig-names.md), [Audio](docs/extraction/audio.md).

## Layout

| Path | Purpose |
| --- | --- |
| `src/` | Rust CLI: inspect, map, packs, partition, sections, extract |
| `tools/` | Python indexing, extraction, verification, and semantic probes |
| `docs/` | MkDocs Material site with Mermaid diagrams |
| `handoff/` | Verified TSV manifests and semantic reports |
| `plan.md` | Live check/todo list |
| `investigation.md` | Append-only evidence journal |
| `rdna2-spirv/` | Submodule: RDNA2 shader decompiler (separate repository) |

## Quick start

```bash
cargo build
target/debug/rage-tools-vi --help
```

Reproducible full pipeline (index → extract → audio → browser → verify):

```bash
python3 tools/pipeline.py --source SOURCE_ROOT --output output all --resume
# non-empty output requires --resume or --force; --dry-run prints every command
```

Focused tools:

```bash
# stream index, then bulk extraction and verification
python3 tools/stream_index.py ARCHIVE --out output/index/name.tsv
python3 tools/bulk_extract.py ARCHIVE INDEX.tsv OUT_DIR --resume
python3 tools/verify_bulk.py ARCHIVE INDEX.tsv OUT_DIR/manifest.tsv

# one entry / one range
python3 tools/extract_entry.py --archive ARCHIVE --kind zlib --start 0x0 --end 0x1000 --output out.bin

# entry manifests from the payload
python3 tools/pair_entry_manifest.py --archive core_bvh4.rpf --index output/index/core_bvh4.tsv --out entries.tsv
```

## Data policy

`*.rpf`, `output/`, `site/`, `target/`, `cache/`, the bus and extracted corpora
are local-only and ignored. Source archives and multi-gigabyte extractions never
enter Git; verified manifests and their hashes do.

## Sibling project: RDNA2 shaders

The GPU layer is its own repository, included here as a submodule:

| Path | What it does |
| --- | --- |
| `rdna2-spirv/` | Generic AMD RDNA2 (GFX10.x) decompiler: machine code to SPIR-V, with golden buffer and pixel tests |

It is a **separate Git repository**, not part of this history: its own `plan.md`
and `investigation.md` live there. Clone with submodules to get it:

```bash
git clone --recurse-submodules https://github.com/lynxnathan/rage-tools-vi.git
git submodule update --init --recursive      # in an existing clone
```

## License

MIT — see [LICENSE](LICENSE).
