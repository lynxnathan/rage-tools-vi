"""Boot stages, test first: each check names the next thing that must become true.

`tests/test_boot_frames.py` is the acceptance test — a window, content, the menu, and a click
that answers. It fails at its first check today, which says nothing about *where* the boot is
stuck. This test states the stages underneath it, in the order the image reaches them, so the
next piece of work is the first failing check rather than an opinion:

  1. the image creates its D3D12 device (a line from the shim, not an inference);
  2. it raises no fatal exception within the window (`EXCEPTION_BREAKPOINT` handled by its own
     reporter counts as fatal: the process is aborting);
  3. it stays alive for the whole window;
Windows are deliberately *not* judged here: the acceptance test owns that, with pid, title and
class attribution. This test stops where the boot stops.

    python3 tests/test_boot_stages.py --game-dir <dump>
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))

FAILED = []


def check(name, condition, detail=""):
    print(f"  {'ok  ' if condition else 'FAIL'}  {name} {detail}")
    if not condition:
        FAILED.append(name)
    return condition


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--exe", type=Path, default=ROOT / "cache/exe/game_scarlett_master.exe")
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args()

    if not args.game_dir.is_dir() or not args.exe.is_file():
        print("  skipped (no game directory or executable)")
        return 0
    if not os.environ.get("DISPLAY"):
        print("  skipped (no DISPLAY)")
        return 0
    from rage import proton_wine
    from run_dir import stage
    from test_boot_frames import windows

    wine = proton_wine()
    if wine is None:
        print("  skipped (no Proton wine)")
        return 0
    stubs = ROOT / "cache/stubs"
    subprocess.run([sys.executable, str(ROOT / "tools/stub_dlls.py"), str(args.exe),
                    "--out", str(stubs)], capture_output=True)
    game, _links, _placed = stage(args.game_dir, ROOT / "cache/run", stubs)

    work = Path(tempfile.mkdtemp(prefix="bootstages-"))
    log_path = work / "run.log"
    exe = game / "bootstage.exe"
    exe.write_bytes(args.exe.read_bytes())
    before = windows()
    seen_new = set()
    env = dict(os.environ,
               WINEPREFIX=os.environ.get("PROTON_PREFIX", str(Path.home() / ".proton-vi/pfx")),
               WINEDLLOVERRIDES=os.environ.get("WINEDLLOVERRIDES",
                                               "d3d12=n,b;d3d12core=n,b;dxgi=n,b"),
               WINEDEBUG="+seh", STUB_TRACE="1")
    try:
        with open(log_path, "w") as sink:
            process = subprocess.Popen(["unshare", "-rn", str(wine), str(exe)],
                                       cwd=str(game), env=env, stdout=sink,
                                       stderr=subprocess.STDOUT)
        deadline = time.time() + args.seconds
        while time.time() < deadline and process.poll() is None:
            for known in set(windows()) - set(before):
                seen_new.add(known)
            time.sleep(1)
        alive = process.poll() is None
        if alive:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        exit_code = process.returncode
    finally:
        exe.unlink(missing_ok=True)

    log = log_path.read_text(errors="replace") if log_path.is_file() else ""
    shutil.copy(log_path, ROOT / "cache/boot-stages.log") if log_path.is_file() else None
    device = re.findall(r"D3D12XboxCreateDevice -> 0x([0-9a-f]+) \(device 0x([0-9a-f]+)\)", log)
    created = [line for line in device if int(line[0], 16) == 0]
    fatal = re.findall(r"Unhandled exception 0x[0-9a-f]+", log) + \
        re.findall(r"EXCEPTION_BREAKPOINT", log)

    print(f"  device creations attempted {len(device)}, succeeded {len(created)}")
    check("stage 1: the image creates a D3D12 device", bool(created),
          f"(attempts {len(device)})")
    check("stage 2: no fatal exception", not fatal, f"({len(fatal)} seen)")
    check("stage 3: the process stays alive", alive, f"(exit {exit_code})")
    if seen_new:
        print(f"  note  {len(seen_new)} window(s) appeared; the acceptance test decides whether")
        print("        any of them is the image's, by pid, title and class")

    print()
    print("PASS" if not FAILED else f"FAIL: {len(FAILED)} check(s)")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
