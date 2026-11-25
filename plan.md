# Plan

Live check/todo list. Evidence, measurements and the failures that led here belong in
[investigation.md](investigation.md) and `handoff/`; completed work is one line of state,
not a log.

Last updated: 2026-11-24.

## Current state

- **Corpus:** 22 archives indexed — 4,415,868 ranges / 161.3 GB stored / 365.0 GB
  decoded; every index tiles its archive (`output/index`, 28 tables).
- **Audio:** 70,484 containers / 1,819,816 streams / 28.53 GB of stream data across
  `audio.rpf` and `story000.rpf`. The `0xff25` corpus decodes to **3,008 WAVs /
  100.96 h / 65.0 GiB**, one rejected packet of ~2.4 M.
- **Script schema:** chain `PSIN→LSCH→LENM→LSNS→LGID→LRSC→CHKS` recovered from the
  writer; 1,012/1,012 records parse exactly. 63,288 typed rows, type word at `+0x0c`,
  42 % of rows name their property.
- **Names:** 36,952 hash→name pairs in one registry with confidence; 4.3 % of hash
  values named corpus-wide.
- **Tests:** `tools/rage.py test --tier unit|corpus|all` — 92 checks over four files
  (synthetic parsers, parser fuzzing, corpus invariants, mod round trip). The repository
  gate is `tools/check.sh`, which also runs `cargo test`.
- **Executable:** `game_scarlett_master.exe`, PE32+ x86-64, console image — its import
  table needs `xg_xs`, `d3d12_xs`, `xapu`, `xmem`, `AcpHal`, `XCRDAPI`,
  `XboxBvhBuilder`, `Bink2Scarlett`. `tools/rage.py play` classifies it and names what
  is missing instead of failing silently.

## Open

- [ ] Settle whether the typed row's `c` word is a declaration index or a value
  (`Decay` carries a shared `300000` while byte rows count 0..6).
- [ ] Identify the `CHKS` tag; ten 32-bit candidates are excluded, the size field matches
  80/80.
- [ ] Explain the 36.7 % partial match on the `LSCH` `+0x18` word.
- [ ] Identify the roles of `0x01393259`, `0x16` and `0xaeb623d8`.
- [ ] Find the second component's size law in the 440 composite packs.
- [ ] Identify the four front-region sections (`p3×8`, `p4`, `p5×24`,
  `(p5-p6)×N×p8`) and what fills the region past them.
- [ ] Decode the remaining ~1.7 M Opus streams; the `0xff25` variant now has a working
  path, the others run through the table rules.
- [ ] Content check for every decode path (flatness for audio, pixel stats for images,
  frames against declared for video).
- [ ] ACE1 trailer pairs (15 `u32` fields, 73 streams).
- [ ] Map the script type/class IDs and transforms.
- [ ] Resolve the unnamed object roots.
- [ ] Script object root field roles.
- [ ] Packs active-learning queue.
- [ ] Give `levels` an entry model (728 of 2,044 packs exact).
- [ ] Name the remaining ped-rig bones and weight hashes — needs a new vocabulary
  source, not a wider search.

## Route to running the game

The console image does not need the runtime reimplemented by hand: static recompilation
does it once, on the user's own copy. Project Leonida ({GPL-3.0}) reimplements the console
system software and translates the precompiled RDNA2 programs to SPIR-V for Vulkan; its
own status page says the game does not boot yet, `26,503 / 26,503` shaders translated and
validated.

Two pieces of this repository are the parts of that route that are already measured:

- the RPF9 layout and index (`handoff/`, `output/index/`), which finds and checks a copy
  and reads the archives without the game;
- `rdna2-spirv/`, the RDNA2 → SPIR-V translator, which is the same translation step.

What is *not* on that route: hand-written stubs for the GDK surface. Measured here to stop
at `game.exe+0x2237178` because interface slots need real layouts, which is exactly the
work a recompilation project has to do once and share.

## Blocked

Each needs a specific input, not more effort.

- [ ] **Play the game.** Parked by decision (2026-11-24). Measured to the boundary:
  engine threads start and execution stops at `game.exe+0x2237178` on a zeroed 32-byte
  structure from interface slot 2. Not to be reopened without a PC build or a public
  layout source for the six queried interfaces. Re-entry is one command
  (`tools/rage.py play --stubs --game-dir <dump>`): it rebuilds the stubs, prints the last
  calls and the fault, and `tools/rage.py play` alone re-classifies the image, so a PC
  build is detected without any other change.
- [ ] RPF9 table of contents — content unidentified. `Front B` is a per-entry table for
  206 of 654 packs and composite for the other 448; no 32-bit hash of 36,952 names
  appears in either region.
- [ ] Read the stream's `Read` at `+0x60` — the archive layer copies both buffers
  verbatim, so any transform sits behind that call.
- [ ] Front A milestone on `story000_bvh4.rpf` — needs independent table framing.
- [ ] Exact end of the last `data.rpf` child — needs an independent trailer start.
- [ ] Multi-mip texture tail — needs a multi-mip dictionary.
- [ ] The 331,728-byte `script.rpf` blob — its size is not any single range in the
  index (largest is `0x52da0`).
- [ ] Script bytecode itself: not in a plaintext section; a code-tracing task now that
  the executable is in hand.
- [ ] Type-name vocabulary (`root_type`, `type_tag`) — most likely stored as text inside
  the masked data.

## Not mine

- [ ] `explorer/` — owned by another session.
