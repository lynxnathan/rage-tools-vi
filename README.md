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
