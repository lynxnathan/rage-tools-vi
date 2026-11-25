# Plan

Live check/todo list. Evidence, measurements and the failures that led here belong in
[investigation.md](investigation.md) and `handoff/`; completed work is one line of state,
not a log.

Last updated: 2026-11-24.

## Current state

- **Corpus:** 22 archives indexed — 4,415,868 ranges / 161.3 GB stored / 365.0 GB
  decoded; every index tiles its archive (28 tables in `output/index`).
- **Audio:** 70,484 containers / 1,819,816 streams. The `0xff25` corpus decodes to 3,008
  WAVs / 100.96 h; the other variants run through the table rules.
- **Script schema:** 1,012/1,012 records parse the seven-chunk chain; 63,288 typed rows,
  42 % of them with a named property.
- **Names:** 36,952 hash→name pairs with confidence; 4.3 % of hash values named.
- **Tests:** `tools/rage.py test --tier unit|corpus|all` — 114 checks; the gate is
  `tools/check.sh`, which also runs `cargo test`.
- **Executable:** console image (`xg_xs`, `d3d12_xs`, `xapu`, `xmem`, `AcpHal`,
  `XCRDAPI`, `XboxBvhBuilder`, `Bink2Scarlett`); `tools/rage.py play` classifies it.

## Open

- [ ] Settle whether the typed row's `c` word is a declaration index or a value.
- [ ] Identify the `CHKS` tag.
- [ ] Explain the 36.7 % partial match on the `LSCH` `+0x18` word.
- [ ] Identify the roles of `0x01393259`, `0x16` and `0xaeb623d8`.
- [ ] Find the second component's size law in the 440 composite packs.
- [ ] Identify what the two loaded ranges contain: section 1 is `align16(p3*8)` bytes at
  `obj[+0x10]`, section 2 is `p4 - header[0x30]` bytes at `obj[+0x18]`, both hashed
  content; and reconcile the arena's last term with the measured region sizes.
- [ ] Decode the remaining ~1.7 M Opus streams.
- [ ] Carve the shader programs — the boundary has to come from the loader's table or from
  the streams the index already finds.
- [ ] Content check for every decode path (flatness for audio, pixel stats for images,
  frames against declared for video).
- [ ] ACE1 trailer pairs (15 `u32` fields, 73 streams).
- [ ] Map the script type/class IDs and transforms.
- [ ] Resolve the unnamed object roots.
- [ ] Script object root field roles.
- [ ] Packs active-learning queue.
- [ ] Give `levels` an entry model (728 of 2,044 packs exact).
- [ ] Name the remaining ped-rig bones and weight hashes.

## Candidates on the boot thread

Each line is a route, what would settle it, and where it stands.

- [ ] **GameInput path.** `FUN_1459258a0` caches the object in `DAT_149ab15e8`; after the
  patched guard the code takes the "object is null" branch and calls through null at
  `image+0x5925903`. Settle by finding which global the successful path writes — the stub's
  out-slot argument (`0x6fffffaf6440`) is not the one the code reads.
- [ ] **Interface layouts.** Six GUIDs, slot 2 called as `(object, buffer, 0x20)`. Settle by
  decompiling the callers at `+0x55DEB6E` and `+0x55DE0xx`, which read the returned fields.
- [ ] **Stream class.** The archive ctor passes `stream+0x10/+0x18/+0x20` into the region
  reader. Settle by decompiling the class and its `Read` at `+0x60`; this also unblocks the
  RPF9 table of contents.
- [ ] **PC build.** `tools/rage.py play` re-classifies any image; a PC build removes the
  whole GDK surface. Settle by pointing the tool at one.
- [ ] **Recompilation project.** Its runtime is the same surface done once; settle by
  comparing its interface expectations with the six GUIDs.

## Running the game

Static recompilation of the console image, on the user's own copy: the CPU is x86-64, so
the code runs natively once the console system software is reimplemented, and the
precompiled RDNA2 programs are translated to SPIR-V. This repository is the
reverse-engineering side of that effort — the RPF9 layout and index, and `rdna2-spirv/`
for the translation step. Hand-written stubs for the GDK surface stay off this path
(parked, see `AGENTS.md`).

## Blocked

Each needs a specific input, not more effort.

- [ ] Play the game: needs a PC build, or the console system software implemented by a
  recompilation project. Guard patching moves the stop but not the requirement, and the
  unattended loop needs its backtrace parser fixed first (`tools/boot_loop.py`).
- [ ] RPF9 table of contents: content unidentified; `Front B` is a per-entry table for 206
  of 654 packs and composite for the other 448.
- [ ] Read the stream class: its `Read` at `+0x60`, and the three words at `+0x10`,
  `+0x18`, `+0x20` that the archive ctor passes to the region reader.
- [ ] Front A milestone on `story000_bvh4.rpf` — needs independent table framing.
- [ ] Exact end of the last `data.rpf` child — needs an independent trailer start.
- [ ] Multi-mip texture tail — needs a multi-mip dictionary.
- [ ] The 331,728-byte `script.rpf` blob — not any single range in the index.
- [ ] Script bytecode container — a code-tracing task.
- [ ] Type-name vocabulary (`root_type`, `type_tag`).

## Not mine

- [ ] `explorer/` — owned by another session.
