# Boot thread: resume sheet

Everything below is measured on this machine; each line names the file or command that proves it.
It exists so a fresh session can start in one read instead of re-deriving the session that
produced it. Long form: `investigation.md` (append-only) and `plan.md` (open checks).

## Where the boot stands

| stage | state | evidence |
| --- | --- | --- |
| process starts | yes | `tests/test_boot_stages.py` |
| D3D12 device created | **yes**, `0x706b0080` via vkd3d-proton | log line `D3D12XboxCreateDevice -> 0x0 (device …)` |
| worker threads | **yes**, 16 | `thread: created …` after the hint is delivered |
| survives its own heap faults | yes (committed on touch) | `xmem! commit on touch …` |
| stays alive | **no**, exit 3 | title's own `int3` at `image+0x2478b7b`, after console slot `0x248` fails |
| window / frames / menu | **no** | `tests/test_boot_frames.py`: `window none`, menu SSIM 0.0000 |

The abort is the title's own allocator (`image+0x554f316` → `image+0x661f0` abort), and it prints
nothing: the only output is its Breakpad reporter.

## Reproduce in three commands

```sh
python3 tools/stub_dlls.py cache/exe/game_scarlett_master.exe --out cache/stubs
python3 tools/run_dir.py --game-dir "$RAGE_GAME_DIR" --package-drive g
python3 tests/test_boot_stages.py --game-dir "$RAGE_GAME_DIR"     # stage 3 is the red one
python3 tests/test_boot_frames.py --game-dir "$RAGE_GAME_DIR"     # the acceptance scoreboard
```

## Environment facts that cost time to find

- **Mammoth volume**: the corpus lives on `/run/media/lynxnathan/Mammoth` (NTFS, `sdb2`). It was
  unmounted once mid-session and every run in that window was meaningless — check it first with
  `mountpoint -q`. Remount read-only with `udisksctl mount -b /dev/sdb2 -o ro`.
- **Native DLLs**: a direct `wine` launch loads Wine's builtin `d3d12.dll`, which refuses every
  12_x level. The runs need
  `WINEDLLOVERRIDES=d3d12=n,b;d3d12core=n,b;dxgi=n,b` (the test sets it itself).
- **Drives**: `dosdevices/d::` and `g::` are raw-device entries that shadow a plain symlink; with
  them present `D:`/`G:` exist but are empty. `run_dir.py --package-drive g` repoints `g:`.
- **ConsoleMode**: setting `HKLM\Software\Microsoft\Windows NT\CurrentVersion\OEM\ConsoleMode` to
  any value makes the image `int3` at `image+0x1e1d574`; leaving it unset is the working path.
- **Crash reporter**: it uploads a minidump per fault to `submit.backtrace.io`. Runs are offline by
  default (`unshare -rn`); `--online` lifts that. It writes dumps to `T:`.

## What was fixed (all in the tree)

| piece | file |
| --- | --- |
| staged runs, never writing the dump; package drive | `tools/run_dir.py` |
| d3d12_xs: config contract, device levels, DXGI adapter, `D3D12GetInterface` = E_NOTIMPL, probes | `tools/d3d12_xs.c` (+ `tools/d3d12_shim.py`) |
| Xodus runtime: XSystem/XGame/XNetworking/XUser/XPersistentLocalStorage, connectivity-hint delivery, exports | `tools/patches/xodus-platform.patch` (+ `tools/xgameruntime.py`) |
| xmem: reserve vs commit, commit-on-touch, free kept mapped, physical pages | `tools/stub_custom/xmem.dll.c` |
| d3d12_xs: aggregate-return ABI adaptor (`0xc8`, `0xd0`), console slot `0x180` queue creator forwarded | `tools/d3d12_xs.c` |
| xcrdapi: factory object with a real vtable, staging buffer | `tools/stub_custom/xcrdapi.dll.c` |
| debugger that works on this image | `tools/wine_gdb.py` |
| screen audit and pixel checks | `tools/screen_audit.py`, `tests/test_boot_pixels.py` |

## The next piece, concretely

The fatal jump to 0 was an ABI mismatch, not memory. vkd3d implements aggregate-returning
`ID3D12Device` methods with the explicit return pointer after `this`; the title uses the MSVC
convention (return pointer first, `this` second). `tools/d3d12_xs.c` now patches slots `0xc8` and
`0xd0` with an `xchg rcx, rdx; jmp <original>` thunk, and the heap-property calls no longer
overwrite the device. See the `2026-11-25` journal entry for the store that proved it.

The new stop is the **console device table**. The title creates a `DIRECT` queue through PC slot
`0x40`, a `COPY` queue through slot `0x180` (forwarded to `0x40` for now), an allocator through
`0x48`, then calls slot `0x248` with `(desc, allocator, 0, IID c3827890-4024-474c-98cf-645b51dc4874, out)`.
That slot has no PC equivalent and returns failure, and the title asserts. The public harness
`OnlyMoisties/GTA6-BootTest` names the additions in its `REPORT.md`: `0x180` queue, `0x248`
command list, `0x1b8`/`0x1c8`/`0x1f0`/`0x218`/`0x2b0` PSOs, `0x270`/`0x278` allocators,
`0x360` `GetResourceAllocationInfo1`, `0x3f8`/`0x428` resource variants. The slot map is recorded
in the `2026-11-25` journal entry; the clone lives in `cache/GTA6-BootTest` (untracked).

Order of work: implement those console creators over vkd3d objects (queue and allocator forward;
command list needs its descriptor translated), and add the ABI thunk to `0x360`. Then
`tests/test_boot_stages.py` decides whether the title stops asserting, and the frames test decides
the rest.

The pagefile-section pool from `OnlyMoisties/GTA6-BootTest` is still the candidate for the
GPU-visible heap, but the heap faults are recoverable and are not the current stop.

## Test hygiene, so the scoreboard stays trustworthy

- `tests/test_boot_frames.py --selftest` (notepad) proves the harness can find a window and score
  content; `check.sh` runs it as `frame harness (notepad)`.
- `--diff-frame`, `--black --expect black|content`, `--compare-frame`, `--assert-pixel` are all
  exercised by `tests/test_boot_pixels.py`, including the negative directions.
- Menu reference (local, untracked): `cache/reference/gta-6-pause-menu.webp`, a PS5 capture
  published by ViceManual, credited in `investigation.md`.
