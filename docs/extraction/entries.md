# Entry manifests

The RPF9 index table is masked, so entries are identified from the **payload**
instead: a pack's streams pair into entries, and the declared count N is used as
an independent check rather than as the parser's driver.

## Units

Two payload shapes appear, and each archive uses whichever one its entries have:

- **pair** — a struct stream followed by its data stream. Used by `core_bvh4`
  (208-byte descriptor) and `textures` (256–1,184-byte structs).
- **chain** — a 64 KiB chain group, where a stream continues its predecessor if
  the predecessor decoded exactly 65,536 bytes and this stream starts on the
  align16 boundary of its end. Used by `data` and `navmeshes`.

An entry is emitted only when the pack's item count lands within a small
tolerance of N; each row carries the delta and a `declared_ok` style flag, so a
consumer can filter to exact packs.

## Coverage

| Archive | Unit | Packs verified | Entries | Artifact |
| --- | --- | ---: | ---: | --- |
| `core_bvh4` | pair | 1,214 / 1,282 | 294,614 | `handoff/core-bvh4-entries.tsv` |
| `navmeshes` | chain | 13 / 29 | 25,981 | `handoff/navmeshes-entries-chains.tsv` |
| `data` | chain | 19 / 42 | 6,537 | `handoff/data-entries-chains.tsv` |
| `textures` | pair | 19 / 21 | 1,349 | `handoff/textures-entries.tsv` |

## Verification

Each manifest is checked against its archive index:

- every entry's stream and data offsets exist in the zlib index — **0 missing**;
- no stream appears twice inside a pack — **0 duplicates**;
- entry counts sit within the emit tolerance of N.

The `core_bvh4` residual (20 packs beyond tolerance) is the known family whose
declared N counts child packs or mixed entry shapes; those rows are emitted with
`declared_ok = 0`.

## Why this works without the table

The payload structures are self-describing:

- `core_bvh4`'s descriptor carries the entry's **exact payload size** at `+0xa0`
  (zero-padding verified beyond it), a right-handed orthonormal basis
  (269,105 / 269,106 within 1e-3), and two content ids whose duplicates always
  share one allocated size.
- `textures` and `navmeshes` structs open with tagged self-relative pointers;
  `navmeshes` points outside its own stream, which is why the classifier accepts
  alignment alone as the pointer filter.
- Chain grouping needs no decode at all, so `data` and `navmeshes` manifests are
  reproducible from the index alone.

## Reproduce

```sh
python3 tools/pair_entry_manifest.py --archive core_bvh4.rpf \
  --index output/index/core_bvh4.tsv --out handoff/core-bvh4-entries.tsv
python3 tools/pair_entry_manifest.py --archive data.rpf \
  --index output/index/data.tsv --unit chains --out handoff/data-entries-chains.tsv
```
