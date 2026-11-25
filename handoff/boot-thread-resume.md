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
| stays alive | **no**, exit 5 | stage 3 fails |
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
| xcrdapi: factory object with a real vtable, staging buffer | `tools/stub_custom/xcrdapi.dll.c` |
| debugger that works on this image | `tools/wine_gdb.py` |
| screen audit and pixel checks | `tools/screen_audit.py`, `tests/test_boot_pixels.py` |

## The next piece, concretely

The title's allocator aborts although every fault of its own is tolerated. The public harness
(`OnlyMoisties/GTA6-BootTest`) crosses this with a **pagefile-section pool**: `XMemVirtualAlloc`
placeholders laid over mapped sections so the title's heap and the GPU see the same pages, plus
`XMemAllocatePhysicalPages` handing out real backing.

Order of work: sections → map placeholders over them → verify with
`python3 tests/test_boot_stages.py` (stage 3 must go green) → then the acceptance run's frames.

Open question worth answering before any of that: **why does the allocator abort** — its frames
are known (`0x554f316` upward) and the abort is deliberate, so a breakpoint there with
`tools/wine_gdb.py` should name the condition in one session.

## Test hygiene, so the scoreboard stays trustworthy

- `tests/test_boot_frames.py --selftest` (notepad) proves the harness can find a window and score
  content; `check.sh` runs it as `frame harness (notepad)`.
- `--diff-frame`, `--black --expect black|content`, `--compare-frame`, `--assert-pixel` are all
  exercised by `tests/test_boot_pixels.py`, including the negative directions.
- Menu reference (local, untracked): `cache/reference/gta-6-pause-menu.webp`, a PS5 capture
  published by ViceManual, credited in `investigation.md`.
