# GTA VI AWC/ADAT decode notes (2026-11-21)

Source: Xbox build `GTA6.Xbox.v1.0.2.1-CYBERLEEK`.
Scope: codec/framing experiments on the extracted `audio-awc` containers.
Status: **container parsed; codec/bitstream not decoded**.

## New container layout

The GTA VI `ADAT` header is not the GTA V AWC layout used by vgmstream.

| Offset | Field |
| --- | --- |
| `0x00` | `ADAT` magic |
| `0x04` | `u16` version = 1 |
| `0x06` | `u16` flags = `0xff21` (all sampled containers) |
| `0x08` | `u16` stream count |
| `0x0c` | `u32` data offset |
| `0x10` | `u16[streams]` stream chunk indexes |
| `0x50` | start of `u64` chunk table; entries end at `data_offset` |

Chunk entry packing remains the earlier `type:8 | size:28 | offset:28` layout.
Chunks observed: `0x55` data, `0x36` peak, `0xA3` seek table, `0x76` format.

## `0x76` format descriptor (32 bytes)

Example (`000000000129b000.awc`, stream 0):

```
45 ed 00 00 ff ff ff ff 80 bb 50 01 45 ed 00 00
00 00 00 00 00 00 00 00 ff ff ff ff 41 34 0b 01
```

| Offset | Interpretation |
| --- | --- |
| `+0x00` | `u32` sample count |
| `+0x04` | `0xffffffff` |
| `+0x08` | `u16` sample rate (48000, 32000, 12000, ...) |
| `+0x0a` | `u16` unknown, likely peak/headroom or block metric (`0x01fc`) |
| `+0x0c` | `u32` sample count again |
| `+0x10` | zero |
| `+0x14` | zero |
| `+0x18` | `0xffffffff` |
| `+0x1c` | `u8` codec ID |
| `+0x1d` | `u8` codec sub-ID (`0x01` or `0x02` observed) |
| `+0x1e` | `u16` zero in all sampled rows |

## Corpus scan

`tools/awc_framing.py --limit 0` parsed **2,320 parsed stream rows / 6,625 containers**
into `handoff/audio-awc-framing.tsv`.

- Codec IDs: **`0x0b` 2,081**, **`0x05` 166**, **`0x02` 73**.
- Rates: 48,000 (2,143), 32,000 (165), 12,000 (10), 28,000 (1), 32,016 (1).
- Codec sub-IDs: `0x01` 2,025, `0x02` 295.
- Data-chunk sizes are multiples of 2,048 bytes; sizes range from 2,048 to
  9,680,896 bytes.
- The 2,048-byte data chunks often begin with **`a0 00 f8`** and repeat the same
  three bytes at **offset 162** (1,451 rows). Six large streams repeat the gap
  pattern `162,...,162,266,162,...` up to the 16-marker scan limit. 840 rows
  have no marker in the first 16 hits, 23 have one, and 6 hit the 16-marker cap.

The marker is therefore a real internal framing signal, not just a fixed prefix.
It is not yet known whether it is a Bink Audio packet marker, an XMA2 frame
header pattern, or a block header around an encrypted payload.

## Decode attempts

### 1. vgmstream AWC

`vgmstream` rejects the GTA VI `ADAT` header because it expects the GTA V AWC
layout. This is a container mismatch, not yet a codec verdict.

### 2. Reconstructed XMA2 WAV

`tools/test_awc_xma2.py` builds `XMA2WAVEFORMATEX` (`wFormatTag=0x0161`,
`BytesPerBlock=2048`, `BlockCount` from `0x55` size), tries mono/stereo and
encoder versions, and decodes with ffmpeg.

Result: xma2 frames are reached, but output is silence or low-level artifacts;
no tonal speech. The previous error `channel len > samples_per_frame` is not
resolved by channel/version/block-count variants.

### 3. Synthetic UEBA/Bink Audio wrapper

`tools/bruteforce_ueba.py` writes an `ABEU` header (UEBA v1), wraps each AWC
payload as `[0x9999][u16 packet_size][payload]`, and feeds vgmstream. vgmstream
accepts the synthetic container and reports `RAD Game tools Bink Audio`.

- Whole `0x55` chunk as one packet: one short burst (~90 ms), then zeros.
- Splitting at 2,048/1,024/512 bytes: silence.
- Offset sweep 0..256 over 20 chunks (5,140 candidates): three non-silent
  candidates, all short bursts; best flatness 0.189 / harmonic 0.619 was a
  single transient, not continuous speech or music.

This establishes that the **Bink Audio container/decoder path is plausible**, but
the AWC payload is not yet a correctly framed Bink packet.

## Current interpretation

1. The container and `0x76` metadata are understood well enough to index every
   stream and compare codecs.
2. `0x0B` is a new codec ID relative to GTA V (`0x05` XMA2, `0x08` Vorbis,
   `0x0D` Opus). `Bink2Scarlett.dll` and the UEBA path make **Bink Audio 2** the
   strongest hypothesis, but it is not proven while the payload decodes to
   transients only.
3. The `a0 00 f8` / `162`-byte marker is the next concrete framing lead.
4. If marker splitting still yields silence, test whether the `0x55` payload is
   **AWC/XXTEA-encrypted**. GTA V AWC has an encrypted-data flag and a
   `.awckey`; GTA VI may use the same pattern. No key is present in the build
   tree sampled so far.

## Reproduction

```bash
# container/stream inventory
python3 tools/awc_framing.py --limit 0

# synthetic Bink Audio sweep (needs numpy + vgmstream-cli)
/tmp/audio-venv/bin/python tools/bruteforce_ueba.py --workers 32 --max-offset 256

# XMA2 wrapper sweep (needs numpy + ffmpeg)
/tmp/audio-venv/bin/python tools/test_awc_xma2.py --limit 5
```

## Artifacts

- `handoff/audio-awc-framing.tsv` — per-stream codec/rate/size/marker table.
- `tools/awc_framing.py` — parser used to generate it.
- `tools/bruteforce_ueba.py` — synthetic UEBA packet sweep.
- `tools/test_awc_xma2.py` — XMA2 WAV wrapper sweep.
- `output/audio-tests/` — local-only WAV/spectrogram experiments (ignored).
