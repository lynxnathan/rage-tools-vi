# Plan

Live check/todo list: open checks only. Evidence, measurements and the failures that led
here belong in [investigation.md](investigation.md) and `handoff/`; the boot thread also has
a one-read resume sheet at [handoff/boot-thread-resume.md](handoff/boot-thread-resume.md).

Last updated: 2026-11-28.

## Format and corpus

- [ ] Settle whether the typed row's `c` word is a declaration index or a value.
- [ ] Identify the `CHKS` tag.
- [ ] Explain the 36.7 % partial match on the `LSCH` `+0x18` word.
- [ ] Identify the roles of `0x01393259`, `0x16` and `0xaeb623d8`.
- [ ] Find the second component's size law in the 440 composite packs.
- [ ] Identify what the two loaded ranges contain (section 1 is `align16(p3*8)` bytes at
  `obj[+0x10]`, section 2 is `p4 - header[0x30]` bytes at `obj[+0x18]`, both hashed
  content), and reconcile the arena's last term with the measured region sizes.
- [ ] Identify the RPF9 per-entry table's content (206 per-entry packs, 448 composite); the
  stream class `Read` is the unread link.
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
- [ ] Reach the Front A milestone on `story000_bvh4.rpf` (four exact XML ranges) with
  independent table framing.
- [ ] Locate the exact end of the last `data.rpf` child from an independent trailer start.
- [ ] Place the 331,728-byte `script.rpf` blob: it is not any single range in the index, so
  this is a code-tracing task.
- [ ] Locate the script bytecode container (code tracing).
- [ ] Extend the type-name vocabulary (`root_type`, `type_tag`).
- [ ] Decide `bulk_extract`'s policy for a stream rejected by the indexed decoded length: it
  currently aborts the batch through `future.result()`. Count, report and skip, or stop?

## Boot thread

- [ ] Turn stage 3 of `tests/test_boot_stages.py` green: stage 2 is green and the title now
  reaches device slots `0x270`/`0x278` (console allocator-pool setup, called from
  `image+0x247ab10`). They need the state the initializer expects — `S_OK` alone makes it
  return false and hit `int3` at `image+0x19f4f58`. Then implement the remaining console
  creators from the public table — queue `0x180` (forwarded), command list `0x248` (proxied),
  PSO `0x1b8`/`0x1c8`/`0x1f0`/`0x218`/`0x2b0`, resources `0x3f8`/`0x428` — and apply the ABI
  thunk to `0x360` (`GetResourceAllocationInfo1`).
- [ ] Pass `tests/test_boot_frames.py` (a real window, content frames, then a static screen
  after the videos): land the four port pieces in order — `xmem` GPU-visible pool plus the
  `G:` redirect; `d3d12_xs` COM device/queue/command-list objects with `PresentX`;
  `XCRDAPI` synchronous DirectStorage queue; `rdna2-spirv` at dispatch. Check with
  `--compare-frame` against the package's `xbs_splash.png`.
- [ ] Satisfy the first guard at `image+0x2237178`: what fills the object field it tests
  (`obj+0xc`, zero from the constructor at `image+0x582a610`), and the value its
  `L"D:\LocalDumps"` lookup in the container at `image+0x56eb30` wants.
- [ ] Find what signals the manual-reset startup event on the platform, then why the
  allocator returns NULL once the 16 worker threads run.
- [ ] Answer the title, sandbox and language queries from `MicrosoftGame.Config`
  (`7952987A`) and the package's `microsoft_gameconfig.bin`.
- [ ] Identify the uncaught exception behind the five-guard CRT abort
  (`VCRUNTIME140+0x1989`, `_XcptFilter` returns 1; the frames are all inside the image).
- [ ] Find where the GameInput object is created before `FUN_1459258a0` caches it in
  `image+0x9ab15e8`.
- [ ] Read the stream class: its `Read` at `+0x60`, and the ctor words at `+0x10`,
  `+0x18`, `+0x20` that the archive ctor passes to the region reader.
- [ ] Fix `tools/boot_loop.py` backtrace parsing so the unattended guard loop reports
  usable stops.

## Blocked on a specific input

- [ ] Play the title / reach the first UI screen: needs a PC build or the console system
  software from a recompilation project. Guard patching moves the stop but not the
  requirement.
- [ ] Publish the six queried interface layouts (slot 2 is called as
  `(object, buffer, 0x20)`; callers at `+0x55DEB6E` and `+0x55DE0xx`): needs a public
  layout source or a PC build.
- [ ] Multi-mip texture tail: needs a multi-mip dictionary.
