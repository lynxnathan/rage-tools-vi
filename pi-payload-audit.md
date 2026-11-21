# RPF9 archive-only payload audit

Scope: read-only inspection of this checkout's `{common,script,core_licenses_data,appdata0}.rpf`
archives and extracted `output/common.rpf` XML. No executable, key, decryption, or
filename recovery was used. All ranges are start-inclusive, end-exclusive.

Reproduce all measurements below with:

```sh
cargo build --locked
python3 tools/pi_archive_audit.py .
```

The script reads the archives and calls the existing `map`/`extract-zlib` commands; it writes only a
temporary decoded object. Categories stay separate: checksum-valid zlib streams are verified by the
zlib decoder, structurally validated objects pass their own parser, candidate ranges are the range
map's groups, and confirmed archive entries require a decoded archive record that predicts a range.
No confirmed archive entries were obtained.

## 1. The two partial DEFLATE ranges in common.rpf

Both spans start with the zlib wrapper `78 da`. The following raw-DEFLATE results start at span
offset 2 and use `zlib.decompressobj(-15)`.

| Range | Stored bytes | Raw result | Decoded | Adler-32 |
| --- | ---: | --- | ---: | --- |
| `0x212190..0x212f20` | 3,472 | failure `0x212437`, `invalid bit length repeat` | 5,239 | not reachable |
| `0x21ba50..0x21d0dd` | 5,773 | raw end `0x21c5f7` | 71,243 | stored `7ae22a8e`, calculated `e8db2239` |

### `0x212190..0x212f20`

The failure is reproduced exactly at `0x212437`, after 5,239 decoded bytes. This is not an arbitrary
zlib stop: the first raw-DEFLATE block is a non-final dynamic block from bit 0 to bit 4,760. It ends
at archive byte `0x2123e5` and emits 5,239 bytes. The next dynamic block starts at `0x2123e5`; at
`0x212435` its code-length decoder reads repeat symbol 18 with count 11 when only 4 of the 316
code-length slots remain (312 -> 323). zlib rejects that overflow at `0x212437`. There is no end of
stream and no Adler-32 to compare.

The decoded prefix is not unrelated data. The preceding candidate chain at `0x210a70` has two
checksum-valid 65,536-byte chunks. Its last bytes are `<penetrationResistance value="16.` and the
partial span starts `0"/>...`, continuing the same XML item. The span is therefore a damaged third
continuation of that chain, not a complete entry. Its output remains unverified.

### `0x21ba50..0x21d0dd`

Raw DEFLATE ends at `0x21c5f7` after 71,243 decoded bytes. The four bytes at the end are the expected
big-endian zlib trailer `7a e2 2a 8e`, but the calculated Adler-32 is `e8db2239`. There are 2,790
stored bytes after the raw end, or 2,786 after the apparent four-byte trailer. The whole deflate
payload is a single final dynamic block from bit 0 to bit 23,847; there is no internal block boundary
at 64 KiB.

The preceding stream at `0x21ad30` is a checksum-valid 65,536-byte chunk. Its decoded tail is
`...<tags>\r\n\t\t` and this span starts `\n\t\t\t<Item>...`, so it initially continues that chain
correctly. The text degrades inside this same deflate block: the first malformed tag is at decoded
offset `0xf002` (61,442) of this stream, before this stream's own 64 KiB boundary. The first 64 KiB
of output is not a reliable decoded-length baseline here. The decoded bytes and text are unverified.

## 2. The 483 root IDs against 1,012 PSIN records

The 42-stream object is 2,702,384 bytes: 30,683 records, 483 roots, and 30,200 tagged references.
Of the 483 roots, 482 occupy 32-byte records and one occupies 48 bytes. Tagged-reference positions
cluster on 8-byte record-relative offsets: 12,335 at +16, 5,184 at +24, 2,201 at +48, 1,641 at +32,
1,422 at +56, and 666 at +64; modulo 16 they are only 0 or 8.

All 1,012 PSIN records have the same section sequence. Every `LGID` section has size 8, i.e. the
section header only and no body. Scanning all 3,474,836 four-byte windows of all records in both byte
orders found exactly three direct 32-bit coincidences:

| Root | ID | Record | Stored chain | Record length | Offset | Byte order | Section |
| ---: | --- | ---: | --- | ---: | ---: | --- | --- |
| 211 | `0x39d6779e` | 335 | `0x237000` | 2,544 | `0x841` | little | `LSNS+0x169` |
| 355 | `0xb79c1bf5` | 1009 | `0x415000` | 5,328 | `0xf97` | big | `LSNS+0x40f` |
| 358 | `0xae679517` | 1010 | `0x417000` | 119,920 | `0xf74` | little | `PSIN+0xf74` |

This reproduces Codex's two `LSNS` and one `PSIN` coincidences. The record-relative positions,
sections, and byte orders do not agree. The three record lengths are not clustered. For 483 distinct
32-bit IDs and 3,474,836 windows in two byte orders, the random expectation is about 0.78 matches;
three is not a population match. These are not enough to identify a shared field or name. No names
are assigned to the IDs.

## 3. The repeated motif in the script.rpf opaque span

At raw-span offset `0x14470` (archive `0x16480`), the exact period is seven bytes:

```text
7e9e81e0e71908
```

It repeats 54 times contiguously from raw `0x14470` to `0x145ea`, archive `0x16480` to `0x165fa`
(378 bytes). The earlier 112-byte observation is 16 repeats of this period; the 16-byte-aligned
"three times 112 plus 32" snapshot stops at 368 bytes, ten bytes before the full run ends. The three
full 112-byte copies are at archive `0x16480`, `0x164f0`, and `0x16560`; the 32-byte prefix starts at
`0x165d0`, followed by ten more period bytes through `0x165f9`.

Searching the seven 16-byte blocks of the 112-byte snapshot on 16-byte boundaries found hits only
inside that same run. The search covered 126 range-map `unclassified` spans: 117 in common.rpf, 5 in
script.rpf, 2 in core_licenses_data.rpf, and 2 in appdata0.rpf. Blocks 0 and 1 occur 4 times
(including the partial fourth copy), blocks 2-6 occur 3 times; there are zero hits outside the run.
No 112-byte copy or seven-byte period was found on a 16-byte boundary in another span.

This supports only a localized 378-byte run with a seven-byte period. It does not identify a cipher,
key, compression codec, or entry boundary, and it gives no cross-span recurrence to test a cipher.
The seven-byte period is not a 16-byte block-cipher period, but that observation alone does not
select a layout or encoding.

## 4. Directory/index evidence in common.rpf

The header word at +0x24 is 418. The current payload map contains:

- 954 checksum-valid zlib streams;
- 277 candidate zlib chains, of which 259 reconstruct complete, structurally validated XML documents;
- 117 candidate opaque spans, totaling 210,272 stored bytes;
- 277 + 117 = 394 candidate groups;
- 0 confirmed archive entries, because no decoded archive record predicts any stored range.

There is no decoded directory or index record. The +0x24 value is count-like, but the payload
heuristic leaves 24 more than the 394 candidate groups. That difference cannot be assigned to
directory records without forcing a partition: an opaque span may be one entry, several entries, or
part of an adjacent entry. The small controls are consistent with +0x24 counting candidate objects,
not a separate directory table, but they do not prove what common.rpf's 418 counts.

The seven same-archive XML associations are:

| Document | Internal ID | Same-archive referenced path |
| --- | --- | --- |
| `00b000.xml` | `core_binks` | `$(root)/changesets/ccs_core_binks.meta` |
| `00c000.xml` | `core_credits` | `$(root)/changesets/ccs_core_credits.meta` |
| `00c160.xml` | `core_credits_movie` | `$(root)/changesets/ccs_core_credits_movie.meta` |
| `00c570.xml` | `core_init_level_with_map_unloaded_misc` | `$(root)/changesets/ccs_core_init_level_with_map_unloaded_misc.meta` |
| `00d000.xml` | `core_language` | `$(root)/changesets/ccs_core_language.meta` |
| `010b70.xml` | `core_stinger_binks` | `$(root)/changesets/ccs_core_stinger_binks.meta` |
| `012490.xml` | `core_vfx` | `$(root)/changesets/ccs_core_vfx.meta` |

The HMAP association is `common:/data/levels/americas/heightmap.dat` from the level manifest. These
eight same-archive candidate paths form a trie with 14 nodes: 8 leaves and 6 directory/prefix nodes.
That can constrain at most eight candidate file leaves and a few shared parents. It cannot decide
whether 418 counts files, directories, or both, and it supplies no evidence for a directory-record
table. No external names were used.

## Limits and branch

The first span has no recoverable Adler-32 or true decoded length; the second has a usable trailer
but a mismatching calculated checksum, so neither is a checksum-valid stream. The three root-ID
coincidences are not a decoded field mapping. The 378-byte motif does not establish a cipher or an
entry boundary. common.rpf still has no decoded entry/index record, so entry count and directory
records remain unestablished.

