# Audio (`audio.rpf`)

`audio.rpf` contains **6,625 `ADAT` AWC containers / 23.51 GB**. The GTA VI
container is a new layout, not the GTA V AWC format parsed by vgmstream.

## Container

| Offset | Field |
| --- | --- |
| `0x00` | `ADAT` magic |
| `0x04` | `u16` version = 1 |
| `0x06` | `u16` flags = `0xff21` |
| `0x08` | `u16` stream count |
| `0x0c` | `u32` data offset |
| `0x10` | `u16[streams]` stream chunk indexes |
| `0x50` | `u64` chunk table, ending at `data_offset` |

Chunk packing is `type:8 / size:28 / offset:28`. Data chunks are multiples of
2,048 bytes.

The `0x76` descriptor is 32 bytes: sample count at `+0x00`/`+0x0c`, sample rate
at `+0x08`, codec at `+0x1c`, and codec sub-ID at `+0x1d`.

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
