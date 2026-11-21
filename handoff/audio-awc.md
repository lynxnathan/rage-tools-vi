# audio.rpf AWC extraction report

Source: Xbox build `GTA6.Xbox.v1.0.2.1-CYBERLEEK`.
Scope: raw AWC containers, container/framing analysis, and decode experiments.

## Result

- AWC magic `ADAT` at `0x129b000` inside `audio.rpf`.
- Extracted **6,625 containers**, **23,510,389,456 bytes** (22 GB).
- Manifest: `manifest.tsv` with start/end, flags, streams, data_offset, SHA-256.
- Header: version 1, flags `0xff21`, 6–24 streams, `data_offset` consistent.
- Chunk types observed: `0x55` data, `0x36` peak, `0xA3` seektable,
  `0x76` new format/stream chunk.
- `0x76` carries sample rate, sample counts, codec ID, and a codec sub-ID.
- Data chunk sizes are multiples of **2048** bytes.

## Framing scan

`tools/awc_framing.py --limit 0` parsed **2,320 stream rows** from the 6,625
containers into `handoff/audio-awc-framing.tsv`.

- Codecs: `0x0b` 2,081; `0x05` 166; `0x02` 73.
- Rates: 48,000 (2,143), 32,000 (165), 12,000 (10), 28,000 (1), 32,016 (1).
- Codec sub-IDs: `0x01` 2,025; `0x02` 295.
- `0x76` is a 32-byte descriptor: sample count at `+0x00`/`+0x0c`, rate at
  `+0x08`, codec at `+0x1c`, sub-ID at `+0x1d`.
- Many 2,048-byte data chunks start with `a0 00 f8` and repeat the same three
  bytes at **offset 162** (1,451 rows). This is a genuine internal framing
  signal; the packet/frame table is still undecoded.

## Decode attempts

- `vgmstream` AWC parser: rejects the GTA VI `ADAT` header (expects GTA V AWC).
- ffmpeg XMA2 with reconstructed `XMA2WAVEFORMATEX`:
  - decoder reaches `xma2` at the expected rate;
  - output is silence/artifacts across mono/stereo and encoder variants.
- Synthetic UEBA/Bink Audio wrapper (`ABEU` + `9999` packet headers):
  - vgmstream accepts it and reports `RAD Game tools Bink Audio`;
  - whole chunk decodes as a short burst only; 2,048/1,024/512 splits are silence;
  - offset sweep produced three one-burst candidates, no continuous audio.

## Interpretation

The container is clear. The codec is not GTA V XMA2/Vorbis/Opus directly;
`0x0B` is a new ID, and `Bink2Scarlett.dll` plus the UEBA path make **Bink Audio
2** the strongest hypothesis. That is **not proven** while the payload only
decodes to transients.

The next concrete lead is the `a0 00 f8` / 162-byte marker. If marker-based
packet splitting fails, test whether the `0x55` payload is AWC/XXTEA-encrypted
(GTA V has an encrypted-data flag and `.awckey`; no GTA VI key was found in the
sampled build tree).

Full experiment log: `handoff/audio-awc-decode.md`.

## Artifacts

- `output/extracted/audio-awc/` — 6,625 `.awc` + `manifest.tsv`
- `handoff/audio-awc-framing.tsv` — per-stream codec/rate/size/marker table
- `handoff/audio-awc-decode.md` — detailed decode experiments
- `tools/extract_awc.py` — ADAT scanner/extractor
- `tools/awc_framing.py` — header/chunk/marker inventory
- `tools/bruteforce_ueba.py` — Bink Audio packet sweep
- `tools/test_awc_xma2.py` — XMA2 wrapper sweep
- `output/audio-awc-verification.tsv` — not yet generated
