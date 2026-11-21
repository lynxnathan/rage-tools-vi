# audio.rpf AWC extraction report

Source: Xbox build `GTA6.Xbox.v1.0.2.1-CYBERLEEK`.
Scope: raw AWC containers; no lossy decode yet.

## Result

- AWC magic `ADAT` at `0x129b000` inside `audio.rpf`.
- Extracted **6,625 containers**, **23,510,389,456 bytes** (22 GB).
- Manifest: `manifest.tsv` with start/end, flags, streams, data_offset, SHA-256.
- Header: version 1, flags `0xff21`, streams 6–24, `data_offset` consistent.
- Chunk types observed: `0x55` data, `0x36` peak, `0xA3` seektable,
  `0x76` new format/stream chunk.
- `0x76` carries sample rate **48000** and sample-count-like fields.
- Data chunk sizes are multiples of **2048** (2048 / 6144).

## Decode attempts

- `vgmstream` (AWC/XMA support): does not recognize this AWC variant.
- ffmpeg XMA2 with reconstructed `XMA2WAVEFORMATEX`:
  - decoder sees `xma2` at 48 kHz;
  - fails with `broken frame: channel len > samples_per_frame`.
- ffmpeg XMA1 tag: invalid input.

## Interpretation

The container is clear; the codec/wrapper is not GTA V AWC and not directly
accepted by vgmstream. The 2048-byte block structure is consistent with
XMA2/Bink-style audio, but the XMA2 bitstream header reconstruction is not
correct. Next step is to reverse the `0x76` chunk layout and the stream-info
table, then rebuild the codec header (XMA2 or Bink Audio).

## Artifacts

- `output/extracted/audio-awc/` — 6,625 `.awc` + `manifest.tsv`
- `tools/extract_awc.py` — ADAT scanner/extractor
- `output/audio-awc-verification.tsv` — not yet generated
