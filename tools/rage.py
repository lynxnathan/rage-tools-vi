"""One entry point for the project's operations.

Shell wrappers grew one per task; this replaces them with subcommands so the surface is
discoverable (`rage.py --help`) and each operation is testable Python.

    python3 tools/rage.py check                 # tests, invariants, docs
    python3 tools/rage.py e2e                   # every end-to-end check, headless
    python3 tools/rage.py demo [DIR]            # playable audio from three variants
    python3 tools/rage.py mod ARCHIVE START END --marker TEXT
    python3 tools/rage.py coverage              # classified share per archive
    python3 tools/rage.py docs                  # regenerate tool index and handoff manifest
    python3 tools/rage.py index adat|bink ARCHIVE
"""

import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

DEMO_RUNS = [
    ("ff21", 0x129B000, 0x12A2000, "stream", 0),
    ("ff02", 0x16437000, 0x16BAA000, "stream", 0),
    ("ff25", 0x548F000, 0x58AF800, "ff25", 0),
]
DEFAULT_AUDIO = Path("/home/lynxnathan/gta6-source/audio.rpf")


def python():
    return [sys.executable]


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, **kwargs)


def say(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name} {detail}")
    return ok


def cmd_check(args):
    return run([str(ROOT / "tools/check.sh")]).returncode


def cmd_e2e(args):
    scripts = sorted((ROOT / "tools").glob("explorer_*e2e*.sh"))
    failures = 0
    for script in scripts:
        print(f"{script.name:40s} ", end="", flush=True)
        result = run(["bash", str(script)], capture_output=True, text=True)
        if result.returncode == 0:
            print("PASS")
        else:
            print("FAIL")
            print("\n".join(result.stdout.splitlines()[-3:]))
            failures += 1
    with tempfile.TemporaryDirectory() as work:
        ok = mod_roundtrip(ROOT / "common.rpf", 0x3B2850, 0x3B399E, b"E2E_OK", Path(work))
        print(f"{'in-place replacement':40s} {'PASS' if ok else 'FAIL'}")
        failures += 0 if ok else 1
        ok = demo(Path(work) / "demo", DEFAULT_AUDIO, quiet=True)
        print(f"{'playable audio':40s} {'PASS' if ok else 'FAIL'}")
        failures += 0 if ok else 1
    print()
    print("PASS" if not failures else f"FAIL: {failures}")
    return 0 if not failures else 1


def pack_replacement(payload, room):
    stream = zlib.compress(payload, 9)
    if len(stream) > room:
        return None
    return stream + b"\0" * (room - len(stream))


def mod_roundtrip(archive, start, end, payload, work):
    if not archive.is_file():
        return False
    copy = Path(work) / "mod.rpf"
    shutil.copy(archive, copy)
    size_before = copy.stat().st_size
    stored = copy.read_bytes()[start:end]
    packed = pack_replacement(payload, len(stored))
    if packed is None:
        return False
    with copy.open("r+b") as handle:
        handle.seek(start)
        handle.write(packed)
    check = zlib.decompress(copy.read_bytes()[start:end])
    return check == payload and copy.stat().st_size == size_before


def cmd_mod(args):
    archive = args.archive
    stored = archive.read_bytes()[args.start:args.end]
    original = zlib.decompress(stored)
    payload = args.payload.read_bytes() if args.payload else args.marker.encode()
    packed = pack_replacement(payload, len(stored))
    print(f"asset {len(original):,} B -> {len(payload):,} B into {len(stored):,} B stored")
    if packed is None:
        print("replacement does not fit")
        return 1
    if args.dry_run:
        print("dry run")
        return 0
    with archive.open("r+b") as handle:
        handle.seek(args.start)
        handle.write(packed)
    check = zlib.decompress(archive.read_bytes()[args.start:args.end])
    return 0 if check == payload else 1


def demo(dest, archive, quiet=False):
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    for variant, start, end, mode, stream in DEMO_RUNS:
        out = dest / f"{variant}-{stream}.wav"
        command = python() + [str(ROOT / "tools/decode_adat_stream.py"), str(archive),
                              "--start", hex(start), "--end", hex(end), "--output", str(out)]
        command += ["--ff25"] if mode == "ff25" else ["--stream", str(stream)]
        result = run(command, capture_output=True, text=True)
        if result.returncode != 0 or not out.is_file():
            if not quiet:
                print(f"{variant}: {result.stdout[-120:]}{result.stderr[-160:]}")
            return False
        with wave.open(str(out)) as handle:
            frames, channels, rate = handle.getnframes(), handle.getnchannels(), handle.getframerate()
        rows.append((out.name, frames / rate, channels,
                     hashlib.sha256(out.read_bytes()).hexdigest()[:16]))
    if not quiet:
        print(f"{'file':14s} {'seconds':>8s} {'ch':>3s}  sha256")
        for name, seconds, channels, digest in rows:
            print(f"{name:14s} {seconds:8.2f} {channels:3d}  {digest}")
    return all(seconds > 0.2 for _n, seconds, _c, _d in rows)


def cmd_demo(args):
    archive = args.archive or DEFAULT_AUDIO
    ok = demo(args.dest, archive)
    if not args.quiet and ok:
        print(f"\nplay: ffplay {args.dest}/ff25-0.wav")
    return 0 if ok else 1


def cmd_measure(args):
    """Audio duration of the 0xff25 corpus, from a sample of containers."""
    import csv
    from decode_adat_stream import ff25_packets
    rows = [r for r in csv.DictReader(open(args.census), delimiter="\t")
            if r["flags"].lower().endswith(args.suffix)]
    if not rows:
        print("no matching containers")
        return 1
    step = max(1, len(rows) // args.sample)
    sample = rows[::step][: args.sample]
    total_packets = 0
    sampled_bytes = 0
    with args.archive.open("rb") as handle:
        for row in sample:
            start, end = int(row["start"], 16), int(row["end"], 16)
            handle.seek(start)
            blob = handle.read(end - start)
            sampled_bytes += len(blob)
            total_packets += len(ff25_packets(blob))
    seconds = total_packets * 960 / 48000
    per_container = seconds / len(sample)
    print(f"containers sampled {len(sample)}  bytes {sampled_bytes:,}  "
          f"packets {total_packets:,}  audio {seconds / 60:.1f} min")
    print(f"per container ~{per_container:.1f} s; "
          f"{len(rows):,} containers -> {per_container * len(rows) / 3600:.1f} h")
    return 0


def cmd_coverage(args):
    from index_coverage import main as coverage_main
    sys.argv = ["index_coverage.py"] + (["--out", str(args.out)] if args.out else [])
    return coverage_main()


def cmd_docs(args):
    for tool, extra in (("tool_index.py", []), ("handoff_manifest.py", [])):
        result = run(python() + [str(ROOT / "tools" / tool)] + extra, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr[-200:])
            return 1
    return 0


def cmd_index(args):
    tool = "adat_index.py" if args.kind == "adat" else "bink_index.py"
    command = python() + [str(ROOT / "tools" / tool), str(args.archive)]
    if args.out:
        command += ["--out", str(args.out)]
    if args.scan:
        command += ["--scan"]
    return run(command).returncode


def cmd_hash(args):
    command = python() + [str(ROOT / "tools/name_hash_game.py"), "--hash"] + args.names
    return run(command).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="run the repository gate").set_defaults(func=cmd_check)
    sub.add_parser("e2e", help="every end-to-end check, headless").set_defaults(func=cmd_e2e)

    demo_p = sub.add_parser("demo", help="decode three AWC variants to WAV")
    demo_p.add_argument("dest", nargs="?", type=Path, default=ROOT / "output/demo")
    demo_p.add_argument("--archive", type=Path)
    demo_p.add_argument("--quiet", action="store_true")
    demo_p.set_defaults(func=cmd_demo)

    mod_p = sub.add_parser("mod", help="replace a zlib range in place")
    mod_p.add_argument("archive", type=Path)
    mod_p.add_argument("--start", type=lambda v: int(v, 0), required=True)
    mod_p.add_argument("--end", type=lambda v: int(v, 0), required=True)
    mod_p.add_argument("--payload", type=Path)
    mod_p.add_argument("--marker")
    mod_p.add_argument("--dry-run", action="store_true")
    mod_p.set_defaults(func=cmd_mod)

    measure_p = sub.add_parser("measure", help="duration of a container variant, sampled")
    measure_p.add_argument("archive", type=Path)
    measure_p.add_argument("--census", type=Path, default=ROOT / "handoff/audio-full-census.tsv")
    measure_p.add_argument("--suffix", default="ff25")
    measure_p.add_argument("--sample", type=lambda v: int(v, 0), default=30)
    measure_p.set_defaults(func=cmd_measure)

    cov_p = sub.add_parser("coverage", help="classified share per archive")
    cov_p.add_argument("--out", type=Path)
    cov_p.set_defaults(func=cmd_coverage)

    sub.add_parser("docs", help="regenerate tool index and handoff manifest").set_defaults(func=cmd_docs)

    idx_p = sub.add_parser("index", help="index an archive's containers")
    idx_p.add_argument("kind", choices=["adat", "bink"])
    idx_p.add_argument("archive", type=Path)
    idx_p.add_argument("--out", type=Path)
    idx_p.add_argument("--scan", action="store_true")
    idx_p.set_defaults(func=cmd_index)

    hash_p = sub.add_parser("hash", help="compute the engine's name hash")
    hash_p.add_argument("names", nargs="+")
    hash_p.set_defaults(func=cmd_hash)

    args = parser.parse_args(argv)
    if args.command == "mod" and not (args.payload or args.marker):
        parser.error("mod needs --payload or --marker")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
