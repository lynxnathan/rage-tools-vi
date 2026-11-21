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
| `0x0b` | 2,081 | Bink Audio 2 hypothesis; framing unresolved |
| `0x05` | 166 | **XMA2; decoded** |
| `0x02` | 73 | unresolved |

`0x05` initially looked broken because the RIFF wrapper used
`wFormatTag=0x0161` (WMAudio2). The correct XMA2 tag is **`0x0166`**. With it,
**151 unique streams decode to 86 MB of PCM WAV**; all 151 are non-silent and
148 have spectral flatness below 0.1. The engine rumble in the decoded set is a
human-confirmed check.

The 15 missing `0x05` rows are fragmented AWC entries, not decoder failures.

## Pending: `0x0B`

`0x0B` is the bulk of the audio. `Bink2Scarlett.dll` is present and a synthetic
UEBA/Bink Audio wrapper is accepted by vgmstream, but it only produces short
transients. The next framing lead is the `a0 00 f8` marker that repeats at
offset **162** in many 2,048-byte data chunks. If marker-based packet splitting
fails, test AWC/XXTEA encryption; no key was found in the sampled build tree.

## Reproduce

```sh
# full audio.rpf output: AWC + framing + XMA2
tools/rebuild_audio.sh SOURCE/audio.rpf output/extracted

# just the XMA2 subset from an existing AWC extraction
python3 tools/extract_awc_xma2.py --limit 0
```

Artifacts: `handoff/audio-awc.md`, `handoff/audio-awc-decode.md`,
`handoff/audio-awc-framing.tsv`, `handoff/audio-xma2-decode.tsv`.
