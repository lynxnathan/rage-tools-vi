# Rage Tools VI

RPF9 archive extraction, range indexing, and object-graph analysis for
GTA VI / Leonida.

The project treats extraction as an evidence problem: every stored byte gets a
range, every payload gets a hash, and every semantic claim is separated from
the deterministic verifier.

## Status

- 8 local RPF9 archives fully covered at the range layer.
- 22 RPF9 source files inventoried; 14 verified, 8 with verified range indexes.
- `packs.rpf`: 144,366 streams / 9.7 GB decoded, verified.
- `anim.rpf`: 130,510 streams / 11.6 GB decoded, verified.
- Script object: 7,960 typed arrays, 3,043 class-0 bones, 1,935 vehicle curves.
- Living MkDocs Material + Mermaid documentation.

Open semantic work: unclassified bytes, metadata cipher, texture codec, and the
Rust 16 MiB payload cap.

## Layout

| Path | Purpose |
| --- | --- |
| `src/` | Rust CLI: inspect, map, packs, partition, sections, extract |
| `tools/` | Python extraction, indexing, verification, and semantic probes |
| `docs/` | MkDocs Material site with Mermaid/UML diagrams |
| `handoff/` | Verified TSV/JSON manifests and semantic reports |
| `plan.md` | Roadmap, state, and working loop |
| `investigation.md` | Append-only evidence journal |

## Build

```bash
cargo build
target/debug/rage-tools-vi --help
```

## Extraction

```bash
python3 tools/extraction_inventory.py
python3 tools/archive_inventory.py
python3 tools/extraction_coverage.py
python3 tools/verify_extraction.py
```

Reproducible full pipeline:

```bash
python3 tools/pipeline.py --source SOURCE_ROOT --output output all --resume
# subcommands: index, extract, audio, pilot, verify
# safety: non-empty output needs --resume or --force; --dry-run prints commands
```

Index-driven bulk extraction:

```bash
python3 tools/extract_entry.py --archive ARCHIVE --kind zlib \
  --start 0x0 --end 0x1000 --output /tmp/out.bin
python3 tools/bulk_extract.py ARCHIVE INDEX_TSV OUT_DIR --resume
python3 tools/verify_bulk.py ARCHIVE INDEX_TSV OUT_DIR/manifest.tsv
```

Large archives use streaming `mmap` index and selective extraction:

```bash
python3 tools/stream_index.py ARCHIVE --out INDEX_TSV
python3 tools/mmap_extract.py ARCHIVE --start 0x0 --end 0x1000 --output /tmp/out.bin
```

## Documentation

```bash
python3 -m venv .venv-docs
.venv-docs/bin/pip install -r requirements-docs.txt
tools/docs.sh serve
```

## Spectral test

```bash
pip install -r requirements-ml.txt
python3 tools/test_audio_spectral.py
```

The test asserts that a harmonic/speech control is tonal while the decoded Bink
candidate is broadband noise.

## Data policy

`*.rpf`, `output/`, `site/`, `target/`, the bus, and extracted corpora are
local-only and ignored. Source archives and verified manifests stay outside Git.

## License

No license has been chosen yet. Treat the repository as private research.
