# Script schema (PSIN)

`script.rpf` records are not bytecode. Each one carries a section sequence —
`PSIN`, `LSCH`, `LENM`, `LSNS`, `LGID`, `LRSC`, `CHKS` — and `PSIN` holds a flat
array of 16-byte rows:

```
struct PsinRow {          // 62,910 rows across 1,012 records
    u32 value;            // union: float when type == 0x102
    u32 type;             // 0x101 int, 0x102 float, 0x103 hash, 0x104 bool, 0x105 byte
    u32 property;         // 301 distinct — names like Position, Flags, Heading
    u32 key;              // 14,653 distinct — names like CAR, bonnet, ambrosia
};
```

Rows are recovered by scanning every record-aligned position and keeping maximal
runs whose type word is in range, because the block directory does not align with
record boundaries at the end of a block.

## Reading it

```bash
python3 tools/psin_extract.py script.rpf          # 62,910 rows -> cache/
python3 tools/psin_dump.py --record 110           # the rows, with names
python3 tools/psin_segment.py --describe 1054     # as paired entries
python3 tools/psin_entries.py                     # every pair, 4,968 of them
```

Record 1054 is the vehicle customisation table:

```
  2  Type=Default      Id=0x00000000
  3  Type=location     Id=CAR
  4  Type=0x00000003   Id=motorbike
  6  Type=0x00000006   Id=cosmetics
  8  Type=0x00000009   Id=bonnet
 10  Type=0x0000000b   Id=side
 13  Type=0x0000000e   Id=roof
```

Two details make that readable and both were learned the hard way: on `Id`/`Type`
rows the payload is the **key** (the value column holds an ordinal), and the
pairing is **local** — only one record in 868 repeats with period 2 throughout, so
the renderer pairs run by run rather than assuming a layout.

## What is named, and what is not

| Namespace | Size | Resolved | How |
| --- | ---: | ---: | --- |
| properties | 301 | 25 | corpus + engine metadata |
| keys | 14,653 | 515 | corpus |
| types (`root_type`, `type_tag`) | 42 | 0 | not a vocabulary problem — see below |

The type namespace is 21 `root_type` and 21 `type_tag` values. Three vocabularies
return nothing against it: the 174k corpus (0 hits, 1.42 expected by chance),
20,300 engine metadata names (4 doubtful hits in 234,720 values), and 40 engine
class names (0 hits). A namespace that small would fall to any decent word list if
its names were plain strings, so the names are most likely stored as text in the
encrypted `LSNS` — the same wall as script decoding.

## What is encrypted

`LSNS` (939 KB across the 1,012 records) is genuinely encrypted: uniform entropy,
deterministic (120 identical bodies of 160 bytes), 16-byte blocked, chained, no
repeating-key structure, and no cipher tables in the shipped binaries. The 331 KB
blob in the same archive has entropy 7.996 and no zlib stream at its start.

Decoding either needs key material or a second sample. The schema above does not:
it is plaintext and complete.
