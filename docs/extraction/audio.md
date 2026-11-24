# Audio (`audio.rpf`)

`audio.rpf` contains **6,625 `ADAT` AWC containers / 23.51 GB**. The GTA VI
container is a new layout, not the GTA V AWC format parsed by vgmstream.

## Container variants

Three flag families are known, and the payload layout differs between them:

| Flags | `data_offset` | Per-stream header | Chunk table | Status |
| --- | --- | ---: | --- | --- |
| `0xff21` | `20 + 42·n` | 42 B | at `0x50`, 8-byte records | decoded |
| `0xff02` | `16 + 60·n` | 60 B | at `0x10 + 4·n` | **decoded** |
| `0xff25` | compact | — | ends at `data_offset` | open |
| `0xff61` | — | — | — | decoded (rare) |

A chunk record is a little-endian `u64` packing `offset:28 | size:28 | type:8`,
so the type byte is the record's high byte. `0xff02` streams own exactly seven
chunks, in order `0x36 0x55 0x5c 0x76 0xa3 0xb2 0xbd`.

| Field | `0xff21` | `0xff02` |
| --- | --- | --- |
| stream index at `+0x10` | `u16[n]`, monotonic | none; `4·n` bytes of per-stream data |
| `data_offset` (6 streams) | `0x110` | `0x82` |
| `0x76` rate | low `u16` at `+0x08` (`0xBB80` = 48 kHz) | same |

The `0x76` descriptor is 32 bytes: sample count at `+0x00`/`+0x0c`, rate as the
low `u16` at `+0x08`, codec at `+0x1c`, codec sub-ID at `+0x1d`. Reading the rate
as a `u32` yields nonsense on both variants.

## The per-stream word

The field that decides how many chunks a stream owns is a single `u32`, and its two
halves do different jobs:

```
 31              3 2   0
+-----------------+-----+
|   stream id     | tags|
+-----------------+-----+
  29 bits           3 bits
```

The tag count sits in the **high three bits**, not the low ones. Reading it as a
plain integer gives a stream id in the millions for ordinary streams, which is what
made the first parser look broken; masking the top three bits yields sensible ids,
and masking the bottom three yields chunk counts that match the chunk table exactly.

This is also why the chunk-table search had to be a suffix scan: the table is
located relative to `data_offset`, and `data_offset` depends on the tag count, so
the two have to be solved together (`tools/awc_chunk_table.py`).

!!! note "Verification state"
    The bit split above is stated in the upstream layout notes and is consistent
    with every stream decoded in this project (93,344 Opus, 1,818 XMA2, 73 ACE1,
    zero failures), but it has not been re-derived as a standalone measurement
    since the extraction volume went offline. Treat it as inherited-but-consistent
    rather than freshly counted.

## `story000` cutscene audio

`story000`'s 9.56 GB unclassified span is a second audio archive: 63,853 AWC
containers, 98.4 % `0xff02`, all codec `0x0b` (Opus) at 48 kHz. Decoding it
produced **196,350 streams / 148.3 hours / 47.7 GB of WAV** in
`output/extracted/story000-opus/`. Opus packets are framed `[u16 size][packet]`
inside `0x800`-byte blocks, the same as `audio.rpf`.

Tools: `tools/awc_framing_ff02.py` (variant census) and
`tools/extract_awc_ff02.py` (WAV export with manifest and SHA-256).

The `0x76` descriptor is 32 bytes: sample count at `+0x00`/`+0x0c`, sample rate
at `+0x08`, codec at `+0x1c`, and codec sub-ID at `+0x1d`.

## Index coverage

The original stream index classified **99.93 % of `audio.rpf` as `unclassified`** —
it recognises compressions, and an AWC bank is neither compressed nor opaque. That
was an *index* gap, not missing data, and it is now closed:

| source | banks | bytes |
| --- | ---: | ---: |
| extraction manifest (`0xff21` pass) | 6,625 | 23,510,392,992 |
| gaps between them (`0xff21` + `0xff02`) | 528 | 4,886,024,192 |
| **total** | **7,153** | **28,396,417,184 = 99.485 %** |

Both variants share one rule: the chunk table holds four records per stream and ends
exactly at `header_size`, with `type:8 | size:28 | offset:28` per record. Only the
table's start differs — `0x50` for `0xff21`, `0x10 + 4·count` for `0xff02`. A bank
ends where its furthest record ends, rounded up to `0x800`.

The residual **0.52 %** is five `0xff61` banks (table offset not established), one
bank whose table does not end at `header_size`, and inter-bank padding.

A caution for anyone reaching for a magic scan: `ADAT` occurs at 7,159 aligned
offsets in `audio.rpf`, and **none** validate against `awc_parse.py`'s tag model,
because that model is the Leonida/story000 layout rather than the `0xff21`/`0xff02`
one. Validating one layout with the other yields confident garbage — which is exactly
what the first 7,159 rejections were.

## Codec status

The corpus scan found 2,320 parsed streams:

| Codec | Streams | Status |
| --- | ---: | --- |
| `0x0b` | 2,081 | **Opus; decoded** |
| `0x05` | 166 | **XMA2; decoded** |
| `0x02` | 73 | **ACE1 impulse responses; decoded** |

### `0x05` = XMA2

The first wrapper used `wFormatTag=0x0161` (WMAudio2), so ffmpeg called the
wrong decoder. The correct XMA2 tag is **`0x0166`**. With it, **151 unique
streams decode to 86 MB of PCM WAV**; all 151 are non-silent and 148 have
spectral flatness below 0.1. The engine rumble in the decoded set is a
human-confirmed check. The 15 missing `0x05` rows are fragmented AWC entries.

### `0x0B` = Opus

Each `0x800`-byte `0x55` block is a sequence of

```text
[u16le packet size][size-byte Opus packet] ...
zero padding to the block end
```

The `a0 00 f8` prefix is a 160-byte packet (`f8` is its TOC); the next packet
starts at 162. libopus decodes the controls at 48 kHz, and every `0xA3` block
boundary matches cumulative decoded frames × channels.

Bulk export: **2,081/2,081 streams / 2.5 GB untrimmed WAV**, zero decode
failures. 11 non-48 kHz streams are decoded at 48 kHz with source rate
recorded; 5 seek flags and 1 encoded silence are preserved. Pre-skip and
end-trim are bounded by controls but not exactly determined.

### `0x02` = ACE1 impulse responses

Each `0x2000`-byte tile is 1,024 interleaved complex float32 bins of a
2,048-point real FFT, stored with the Nyquist bin omitted. Inverse-transform
the tiles, restore the missing alternating Nyquist component from the zero
leading half and adjacent overlaps, concatenate the second halves, and trim to
the tap count at `0x76 +0x0c`. The terminal `0x2000` bytes are an `ACE1`
trailer: `0xfffface1` + 15 LE `u16` pairs + zero padding.

`tools/extract_awc_ace1.py` exported **73/73 streams / 6 MB float32 WAV**; all
controls have overlap/padding RMS below `8e-9`. The first trailer pair values
are not needed for reconstruction and remain unassigned.

## Reproduce

```sh
# full audio.rpf output: AWC + framing + XMA2 + Opus
tools/rebuild_audio.sh SOURCE/audio.rpf output/extracted

# individual subsets from an existing AWC extraction
python3 tools/extract_awc_xma2.py --limit 0
python3 tools/extract_awc_opus.py --limit 0
python3 tools/extract_awc_ace1.py --limit 0
```

Artifacts: `handoff/audio-awc.md`, `handoff/audio-awc-decode.md`,
`handoff/data-awc-opus.md`, `handoff/data-awc-trim-ace1.md`,
`handoff/audio-awc-framing.tsv`, `handoff/audio-xma2-decode.tsv`,
`handoff/audio-opus-decode.tsv`, `handoff/audio-ace1-decode.tsv`.
