"""Replace an asset inside an RPF without touching any other byte.

The GTA V workflow edits an archive in place: find the entry, write new bytes, keep every
other offset valid. The same works here for any entry stored as a zlib range, because a
deflate stream ends before the bytes that follow it — so a replacement can be recompressed,
padded to the original stored length, and written over the range. Readers stop at the
stream end; the archive's offsets and sizes never move.

This is the smallest mod that runs on the VI formats as reversed: same-size replacement,
no re-pack, no writer.

    python3 tools/mod_replace.py ARCHIVE --start 0x12330 --end 0x12548 --payload new.bin
    python3 tools/mod_replace.py ARCHIVE --index output/index/common.tsv --find 0x12330 \\
        --marker HELLO --dry-run
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path


def read_range(archive, start, end):
    with archive.open("rb") as handle:
        handle.seek(start)
        return handle.read(end - start)


def write_range(archive, start, raw):
    with archive.open("r+b") as handle:
        handle.seek(start)
        handle.write(raw)


def pack_replacement(payload, room, level=9):
    """Deflate `payload` into exactly `room` bytes, or fail."""
    stream = zlib.compress(payload, level)
    if len(stream) > room:
        return None, stream
    return stream + b"\0" * (room - len(stream)), stream


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--start", type=lambda v: int(v, 0), required=True)
    parser.add_argument("--end", type=lambda v: int(v, 0), required=True)
    parser.add_argument("--payload", type=Path, help="file whose bytes replace the asset")
    parser.add_argument("--marker", help="or: replace with this text (for a smoke test)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stored = read_range(args.archive, args.start, args.end)
    try:
        original = zlib.decompress(stored)
    except zlib.error as error:
        sys.exit(f"range is not a zlib stream: {error}")

    if args.payload:
        replacement = args.payload.read_bytes()
    elif args.marker:
        replacement = args.marker.encode()
    else:
        sys.exit("give --payload or --marker")

    room = len(stored)
    packed, stream = pack_replacement(replacement, room)
    print(f"asset {len(original):,} B -> replacement {len(replacement):,} B")
    print(f"stored room {room:,} B, recompressed {len(stream):,} B "
          f"({room - len(stream):,} B of padding)")
    if packed is None:
        sys.exit("replacement does not fit in the original stored length")

    if args.dry_run:
        print("dry run: nothing written")
        return 0

    write_range(args.archive, args.start, packed)
    check = zlib.decompress(read_range(args.archive, args.start, args.end))
    ok = check == replacement
    print(f"read back {len(check):,} B, matches: {ok}")
    if not ok:
        return 1
    print("archive offsets unchanged; only the range was written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
