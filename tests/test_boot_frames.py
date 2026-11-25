"""Acceptance test: the console image boots and the screen shows frames.

Defines "it runs" as something measurable rather than as a feeling: the process stays alive
and the display it draws to is not a constant colour. Frames are grabbed from a virtual
display, converted to grayscale, and scored by their spread; a black or uniform screen has a
spread near zero.

Prerequisites, all skipped rather than failed when missing:
  * the image (`cache/exe/game_scarlett_master.exe`),
  * a game directory with the package (`--game-dir` or `RAGE_GAME_DIR`),
  * Proton's wine (`PROTON_WINE` or a Steam/GE installation),
  * `Xvfb` and `ffmpeg` for the virtual display and the grab.

    python3 tests/test_boot_frames.py --game-dir <dump>
    python3 tests/test_boot_frames.py --game-dir <dump> --seconds 30 --min-frames 5
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

FAILED = []


def check(name, condition, detail=""):
    print(f"  {'ok  ' if condition else 'FAIL'}  {name} {detail}")
    if not condition:
        FAILED.append(name)
    return condition


def grab(display, size, sink):
    """One grayscale frame from the virtual display, or None."""
    command = ["ffmpeg", "-v", "error", "-f", "x11grab", "-video_size", size,
               "-i", display, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    result = subprocess.run(command, capture_output=True, timeout=30)
    if result.returncode != 0 or not result.stdout:
        return None
    return result.stdout


def spread(frame):
    """(contrast, deviation, lit fraction) of a grayscale frame.

    A pointer cursor alone gives contrast without content, so the lit fraction is the
    number that decides: it counts pixels brighter than a quarter of full scale.
    """
    if not frame:
        return 0, 0.0, 0.0
    low, high = min(frame), max(frame)
    sample = frame[: 400000]
    mean = sum(sample) / len(sample)
    variance = sum((value - mean) ** 2 for value in sample) / len(sample)
    lit = sum(1 for value in sample if value > 64) / len(sample)
    return high - low, variance ** 0.5, lit


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game-dir", type=Path,
                        default=Path(os.environ["RAGE_GAME_DIR"]) if os.environ.get("RAGE_GAME_DIR") else None)
    parser.add_argument("--exe", type=Path, default=ROOT / "cache/exe/game_scarlett_master.exe")
    parser.add_argument("--seconds", type=int, default=25)
    parser.add_argument("--min-frames", type=int, default=3)
    parser.add_argument("--min-spread", type=int, default=24)
    parser.add_argument("--min-lit", type=float, default=0.02,
                        help="share of pixels above a quarter of full scale")
    args = parser.parse_args()

    if args.game_dir is None or not args.game_dir.is_dir():
        print("  skipped (no game directory; pass --game-dir or set RAGE_GAME_DIR)")
        return 0
    if not args.exe.is_file():
        print("  skipped (no executable)")
        return 0
    if not shutil.which("Xvfb") or not shutil.which("ffmpeg"):
        print("  skipped (Xvfb or ffmpeg missing)")
        return 0
    from rage import proton_wine
    wine = proton_wine()
    if wine is None:
        print("  skipped (no Proton wine; set PROTON_WINE)")
        return 0

    stubs = ROOT / "cache/stubs"
    build = subprocess.run([sys.executable, str(ROOT / "tools/stub_dlls.py"),
                            str(args.exe), "--out", str(stubs)],
                           capture_output=True, text=True)
    if build.returncode != 0:
        print(build.stdout[-300:], build.stderr[-300:])
        return 1
    for dll in stubs.glob("*.dll"):
        shutil.copy(dll, args.game_dir / dll.name)

    work = Path(tempfile.mkdtemp(prefix="bootframes-"))
    display = ":97"
    size = "1280x720"
    screen = subprocess.Popen(["Xvfb", display, "-screen", "0", f"{size}x24"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_path = work / "run.log"
    exe = args.game_dir / "bootframe.exe"
    exe.write_bytes(args.exe.read_bytes())
    env = dict(os.environ, DISPLAY=display, WINEPREFIX=os.environ.get(
        "PROTON_PREFIX", str(Path.home() / ".proton-vi/pfx")), STUB_TRACE="1")
    process = None
    frames = 0
    best = (0, 0.0, 0.0)
    try:
        time.sleep(2)
        with open(log_path, "w") as sink:
            process = subprocess.Popen([str(wine), str(exe)], cwd=str(args.game_dir),
                                       env=env, stdout=sink, stderr=subprocess.STDOUT)
        deadline = time.time() + args.seconds
        while time.time() < deadline:
            if process.poll() is not None:
                break
            frame = grab(display, size, work)
            if frame:
                contrast, deviation, lit = spread(frame)
                if (contrast, deviation, lit) > best:
                    best = (contrast, deviation, lit)
                if contrast >= args.min_spread and lit >= args.min_lit:
                    frames += 1
            time.sleep(1)
    finally:
        alive = process is not None and process.poll() is None
        if process is not None and alive:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        screen.terminate()
        exe.unlink(missing_ok=True)

    log = log_path.read_text(errors="replace") if log_path.is_file() else ""
    exit_code = process.returncode if process is not None else None
    print(f"  exit {exit_code}, frames above threshold {frames}, "
          f"best contrast {best[0]}, deviation {best[1]:.1f}, lit {best[2]:.1%}")

    check("the process starts", process is not None and exit_code is not None)
    check(f"it draws at least {args.min_frames} non-uniform frames", frames >= args.min_frames,
          f"({frames})")
    check("the display is not uniform", best[0] >= args.min_spread, f"({best[0]} levels)")
    check("the screen carries content, not just a cursor", best[2] >= args.min_lit,
          f"({best[2]:.1%} lit)")
    if not frames:
        for line in log.splitlines()[-6:]:
            print(f"    {line}")
    shutil.copy(log_path, ROOT / "cache/boot-frames.log") if log_path.is_file() else None

    print()
    print("PASS" if not FAILED else f"FAIL: {len(FAILED)} check(s)")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
