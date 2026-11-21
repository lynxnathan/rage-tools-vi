# Serialized structs across the corpus

Most entry payloads open with a serialized container struct: eight 4-byte slots
whose values are `0x5`-tagged **self-relative pointers** (`0x50000080` = tag 5,
offset `0x80`), one `0x6`-tagged field, and `{ptr, u16 count, u16 capacity}`
array headers. The scanner identifies a struct when the first `0x40` bytes (at
offset 0, or after a 256-byte payload header) hold at least two such pointers,
where a candidate is a `u32` with upper nibble `5..0xA` and low four bits zero.

Guardrails learned the hard way:

- scan the **header only**; whole-payload scanning invents dozens of pointers
  per 6 MB body;
- `+0xa0` is a **bvh4 class field**, not a container field — it is harvested only
  when the record is 208 bytes and carries the full bvh4 pointer table
  (`0x50000080/a0/b0/c0/50`, `1` at `+0x10`, `0x60000000` at `+0x20`).

## Corpus map

`handoff/struct-summary.tsv` (tool: `tools/struct_harvest.py`).

| Archive | Streams/entry | Struct share | Top segment tag | Tag-5 share | External pointers | Implied attachments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `anim` | 1.54 | 78 % | 5 | 82 % | 0.60 | 0.54 |
| `audio` | 0.12 | 21 % | 10 | 0 % | 2.43 | −0.88 |
| `common` | 2.28 | 25 % | 7 | 0 % | 2.04 | 1.28 |
| `core_bvh4` | 1.92 | 53 % | **6** | 8 % | **0.93** | **0.92** |
| `core_restofworld` | 2.07 | 53 % | 5 | 87 % | 0.25 | 1.07 |
| `data` | 1.24 | 79 % | 5 | 82 % | 0.60 | 0.24 |
| `levels` | 2.13 | 57 % | 5 | 86 % | 0.30 | 1.13 |
| `navmeshes` | 1.40 | 69 % | 5 | 99 % | 0.09 | 0.39 |
| `packs` | 1.80 | 45 % | 5 | 98 % | 0.02 | 0.80 |
| `script` | 1.04 | 1 % | 10 | 0 % | 4.00 | 0.04 |
| `shaders` | 1401.7 | 20 % | 7 | 5 % | 2.70 | 1400.67 |
| `shared_minigame000_bvh4` | 1.94 | 50 % | **6** | 2 % | **0.98** | **0.94** |
| `story000` | 0.88 | 73 % | 5 | 88 % | 0.48 | −0.12 |
| `story000_script` | 0.86 | 23 % | 8 | 0 % | 3.57 | −0.14 |
| `textures` | 2.01 | 52 % | 5 | 94 % | 0.06 | 1.01 |

`movies`, `appdata0` have no zlib streams.

## What the map says

- **Tag 6 is the `*_bvh4` signature.** Both bvh4 archives show tag 6 as the
  dominant segment nibble, exactly one external pointer per struct, and that
  count matches the archive's implied attachment ratio (0.93 vs 0.92 and
  0.98 vs 0.94). No other archive has this profile.
- **Tag 5 dominates elsewhere** (82–99 % of structs in `anim`, `data`, `levels`,
  `navmeshes`, `packs`, `story000`, `textures`): those structs address only
  in-stream sub-structures.
- **Segment tags 7–10 mark the script/audio family**: `script` (tag 10, 4.0
  external/struct), `story000_script` (tag 8, 3.6), `audio` (tag 10, 2.4),
  `common` (tag 7, 2.0), `shaders` (tag 7, 2.7).
- **Struct share tracks entry density**, not archive size: `data` (79 %) and
  `anim` (78 %) are nearly all struct roots, `script` is 1 % (its payloads are
  the object graph), and `levels` (57 %) sits mid-range because its large packs
  hold many data streams per struct.
- The external-pointer count is **not** an attachment counter outside `*_bvh4`:
  distinct-target counting on 2,500 `levels` streams gives 0.54 against 1.13
  implied. The reliable universal proxy is the **struct-root count per pack**,
  which reproduces declared N to ±3 across sampled small `levels` packs.

## Reproduce

```sh
python3 tools/struct_harvest.py \
  --archives levels.rpf:output/index/levels.tsv core_bvh4.rpf:output/index/core_bvh4.tsv \
  --sample 100
```
