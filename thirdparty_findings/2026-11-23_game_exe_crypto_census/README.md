# Third-party static crypto census — game executable (GTA VI v1.0.2.1, Xbox Series)

**Brought in as external findings, offered for cross-checking against this repository's
own probes (`pe_audit.py`, `crypt_battery.py`, `front_b_law_fit.py`, `front_ab_matrix.py`).**
Everything below is a *measurement of a format/binary*, produced statically on the owner's
own working copy. No game data, no binaries, no keys are included. AI-assisted
(Claude Code) — reviewed for production of evidence only, methodology in the script.

## How to reproduce

```bash
python3 -I exe_crypto_fingerprint_scanner.py /path/to/game_scarlett_master.exe
```

The scanner is stdlib-only, windowed (4 MiB), and writes `exe_crypto_census.json`
next to itself. Arguments: the executable path. It touches nothing else.

## What it measured (all claims artifact-backed by the scanner above)

Target: plain, unencrypted PE32+ x64, ~115 MiB, 10 sections
(`.text .rdata .data .pdata .retplne .tls .voltbl .xbld .reloc .xbld`), machine 0x8664.

| Probe | Result |
|---|---|
| 32-byte archive constant `5f08daab…d8aa6989`, six forms (raw / reversed / dword-swap / qword-swap / low-16 / high-16) | **0 hits, every form** — confident NULL |
| AES forward S-box (full / 64 B / 32 B prefixes) | 0 hits |
| AES **inverse** S-box | **exactly 1 hit @ raw file offset `0x5fc1267`** (inside `.rdata`) |
| SHA-256 K-block head, ChaCha `expand 32-byte k` (raw + ascii) | 0 hits |
| AES-NI opcode histogram, `.text` vs `.pdata` control | aesenc **126**, aeskeygenassist **31**, aesenclast 9, aesdec 13, aesdeclast 4 — `.pdata` control **all zero** |
| fourCC census (ASCII / LE-stored) | PSIN 3/3, RPF 0/4, ETPF 2/-, RBF0 2/-, KB2 1/0, RDS5 1/- |
| Debug-dir path | MSVC build path present for `game_scarlett_master` (Xbox Scarlett x64 GXDK layout) |

A ±32 KiB context dig around the inverse S-box (in the sibling artifact set) found:
no companion T-table permutation boxes, no zero-flanked 96–320-byte expanded-key
islands, no XXTEA delta words. Reading: real decrypt-capable AES machinery exists
(hardware-accelerated clusters + a lone software inverse box), but **no static key
blob sits beside it**.

## Why this may interest this repository

`front_b_law_fit.py` / `front_ab_matrix.py` study the same header-word space on the
archive side; `crypt_battery.py` is the closest sibling to the constant-as-key battery
we ran separately (null beyond controls: random-key null mean 0.216 / sd 0.021 /
max 0.304 vs positive control 0.735, ~2000 trials). If any of your probes disagree
with anything tabulated here, the discrepancy is worth a lot to us — that is the point
of sending it. The scanner regenerates the whole table on any copy.
