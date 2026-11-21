# Extraction pilot: audio.rpf + levels.rpf

2026-11-21. Small static read-only browser for the rebuilt corpus. No archive
was reindexed, no payload was re-extracted, and no payload was copied.

## Run

```sh
python3 tools/extraction_index_pilot.py
# open output/extraction-index-pilot/index.html
```

Inputs: `output/index/audio.tsv`, `output/index/levels.tsv`,
`output/extracted/audio/manifest.tsv`, and `output/verification.tsv`.
The generator joins audio ranges to the verified manifest, validates one
decoded file's size and SHA-256, and emits bounded sample pages for levels.

## What it shows

- Root cards for `audio.rpf` (**verified**) and `levels.rpf`
  (**indexed-only**), with source extents, stored/decoded totals, and kinds.
- Bounded 32-row sample pages for levels (first, middle, last) because the full
  index has 2,199,213 ranges; no payload is read.
- Drill-down ranges with start/end, status, source archive, extracted path and
  SHA-256 for verified audio, or `No extracted file is listed` for levels.
- Back navigation to the archive and root; uncertain pack membership remains
  at archive level.

## Validation

`python3 tools/extraction_index_pilot.py` prints:

- `audio 0x5000–0x6316 matched the decoded file and SHA-256
  725398e5f5267e1da78a82b8582a68950d72c3dc8adb0d97b54eda40274c19f2`
- `levels 0x1d000–0x1d701 matched the index; no bulk extraction manifest`

The emitted `output/extraction-index-pilot/index.html` is 602 KB. A Playwright
headless check is available as `tools/verify_extraction_index_pilot.cjs`, but
Playwright is not installed in the base environment.

Artifact: `output/extraction-index-pilot/index.html`; generator:
`tools/extraction_index_pilot.py`.
