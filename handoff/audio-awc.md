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

- **Codec `0x05` = XMA2: solved.** The first wrapper used `wFormatTag=0x0161`
  (WMAudio2), so ffmpeg called the WMA decoder and produced silence/noise. The
  correct XMA2 tag is `0x0166`. `tools/extract_awc_xma2.py` decoded **151 unique
  streams to 86 MB of WAV** (166 rows selected; 15 fragmented entries missing);
  all 151 are non-silent and 148 have flatness < 0.1. This is the first
  non-zlib codec family decoded from `audio.rpf`.
- `vgmstream` AWC parser: rejects the GTA VI `ADAT` header (expects GTA V AWC).
- Synthetic UEBA/Bink Audio wrapper (`ABEU` + `9999` packet headers):
  - vgmstream accepts it and reports `RAD Game tools Bink Audio`;
  - whole chunk decodes as a short burst only; 2,048/1,024/512 splits are silence;
  - offset sweep produced three one-burst candidates, no continuous audio.
- Codec `0x02`: not XMA2; PCM/MS-ADPCM/XMA1 wrappers produce artifacts.

## Interpretation

The container is clear. **`0x05` is XMA2** and now decodes to continuous audio.
`0x0B` remains a new ID; `Bink2Scarlett.dll` plus the UEBA path make **Bink Audio
2** the strongest remaining hypothesis, but it is not proven while payloads only
decode to transients. `0x02` is also unresolved.

The next concrete lead for `0x0B` is the `a0 00 f8` / 162-byte marker. If
marker-based packet splitting fails, test whether its `0x55` payload is
AWC/XXTEA-encrypted (GTA V has an encrypted-data flag and `.awckey`; no GTA VI
key was found in the sampled build tree).

Full experiment log: `handoff/audio-awc-decode.md`.

## Artifacts

- `output/extracted/audio-awc/` — 6,625 `.awc` + `manifest.tsv`
- `handoff/audio-awc-framing.tsv` — per-stream codec/rate/size/marker table
- `handoff/audio-xma2-decode.tsv` — 166 codec-`0x05` rows with decode status/SHA
- `handoff/audio-awc-decode.md` — detailed decode experiments
- `tools/extract_awc.py` — ADAT scanner/extractor
- `tools/awc_framing.py` — header/chunk/marker inventory
- `tools/bruteforce_ueba.py` — Bink Audio packet sweep
- `tools/test_awc_xma2.py` — XMA2 wrapper sweep
- `tools/extract_awc_xma2.py` — codec-`0x05` XMA2 decode/extract
- `output/extracted/audio-xma2/` — 151 decoded WAVs + manifest (local-only)
- `output/audio-awc-verification.tsv` — not yet generated
