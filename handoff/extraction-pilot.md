# Extraction pilot: audio.rpf + levels.rpf

2026-11-21. Small read-only browser for the rebuilt corpus. No archive was
reindexed, no payload was re-extracted, and no payload was copied.

## Run

```sh
python3 tools/extraction_pilot.py --port 8766
# open http://127.0.0.1:8766/
```

Inputs are `output/index/audio.tsv`, `output/index/levels.tsv`,
`output/extracted/audio/manifest.tsv`, and `output/verification.tsv`.
Page size is 100 ranges; `levels` is never loaded as a payload.

## What it shows

- Root cards for `audio.rpf` (**verified**) and `levels.rpf`
  (**indexed-only**), with stored/decoded totals and range-kind counts.
- Bounded archive pages with `start`, `end`, kind, stored/decoded bytes, and
  per-row status (`verified`, `indexed-only`, `unresolved`).
- Range detail with source extent and back link. `audio` joins the verified
  extraction manifest and shows the extracted path, bytes, SHA-256, and PASS
  verdict. `levels` explicitly says there is no extracted file.
- Uncertain pack membership remains at archive level; no pack inference was
  attempted.

## Validation

- `audio.rpf` root: 1,629 ranges; `0x5000..0x6316` resolves to the extracted
  manifest SHA-256
  `725398e5f5267e1da78a82b8582a68950d72c3dc8adb0d97b54eda40274c19f2`.
- `levels.rpf` root: 2,199,213 ranges; `0x1d000..0x1d701` matches the index and
  reports `indexed-only` / no extracted file.
- `/archive?name=levels&page=1000` returns HTTP 200 with a bounded page.
- All HTTP checks returned 200; no reindex or extraction command was run.

Artifact: `tools/extraction_pilot.py`; service path `http://127.0.0.1:8766/`.
