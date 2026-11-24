"""Decode one stream from an AWC container using the indexer's own table rules.

The existing probe expects the `0xff21` layout (data offset at `+0x0c`), so it yields
nothing on the `0xff02` pools that hold most of the corpus. This reads the chunk table
the way `tools/adat_index.py` verified it — four records per stream
(`0x36 0x55 0x76 0xa3`), table at `0x10 + 4*count` for `0xff02` or `0x50` for
`0xff21`, ending exactly at `header_size` — and then decodes the stream's Opus packets
with the libopus walker the project already uses.

    python3 tools/decode_adat_stream.py audio.rpf --start 0x16437000 --stream 0 \
        --output /tmp/stream.wav
    python3 tools/decode_adat_stream.py container.awc --stream 0 --output out.wav
"""

import argparse
import ctypes
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_awc_opus_probe import BLOCK_BYTES, decode_packets, load_opus, split_block

TABLE_AT = {0xFF21: lambda count: 0x50, 0xFF02: lambda count: 0x10 + 4 * count}


def records(blob, count, header_size, flags):
    """The chunk table as (kind, offset, size) triples."""
    start = TABLE_AT[flags](count) if flags in TABLE_AT else None
    if start is None or (header_size - start) % (8 * count):
        raise ValueError(f"unsupported table position for flags 0x{flags:04x}")
    per_stream = (header_size - start) // (8 * count)
    out = []
    for index in range(count * per_stream):
        (raw,) = struct.unpack_from("<Q", blob, start + 8 * index)
        out.append((raw >> 56, raw & 0x0FFFFFFF, (raw >> 28) & 0x0FFFFFFF))
    return out, per_stream


def stream_info(blob, index):
    version, flags, count, header_size = struct.unpack_from("<HHII", blob, 4)
    table, per_stream = records(blob, count, header_size, flags)
    if index >= count:
        raise SystemExit(f"stream {index} out of range (container has {count})")
    chunks = table[index * per_stream:(index + 1) * per_stream]
    data = next(((offset, size) for kind, offset, size in chunks if kind == 0x55), None)
    fmt = next(((offset, size) for kind, offset, size in chunks if kind == 0x76), None)
    if not data or not fmt:
        raise SystemExit("stream has no 0x55/0x76 pair")
    descriptor = blob[fmt[0]:fmt[0] + fmt[1]]
    samples = struct.unpack_from("<I", descriptor, 0)[0]
    rate = struct.unpack_from("<H", descriptor, 8)[0]
    codec, channels = descriptor[0x1C], descriptor[0x1D]
    frames = struct.unpack_from("<I", descriptor, 12)[0] if len(descriptor) >= 16 else 0
    payload = blob[data[0]:data[0] + data[1]]
    return {"flags": flags, "count": count, "rate": rate, "codec": codec,
            "channels": channels, "samples": samples, "frames": frames,
            "payload": payload, "per_stream": per_stream}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("container", type=Path)
    parser.add_argument("--start", type=lambda v: int(v, 0), default=0,
                        help="offset inside an archive file (reads to --end)")
    parser.add_argument("--end", type=lambda v: int(v, 0), default=0)
    parser.add_argument("--stream", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.start:
        if not args.end:
            sys.exit("--start needs --end")
        with args.container.open("rb") as handle:
            handle.seek(args.start)
            blob = handle.read(args.end - args.start)
    else:
        blob = args.container.read_bytes()
    if blob[:4] != b"ADAT":
        sys.exit("not an ADAT container")

    info = stream_info(blob, args.stream)
    print(f"container flags 0x{info['flags']:04x}  streams {info['count']}  "
          f"records/stream {info['per_stream']}")
    print(f"stream {args.stream}: codec 0x{info['codec']:02x}  channels {info['channels']}  "
          f"declared rate {info['rate']} (decoding at 48 kHz)  samples {info['samples']}  "
          f"frames {info['frames']}  payload {len(info['payload']):,} B")
    if info["codec"] != 0x0B:
        sys.exit(f"codec 0x{info['codec']:02x} is not Opus; this tool decodes Opus only")

    payload = info["payload"]
    usable = len(payload) - (len(payload) % BLOCK_BYTES)
    if usable != len(payload):
        payload = payload[:usable]
    packets = sum(len(split_block(payload[i:i + BLOCK_BYTES]))
                  for i in range(0, len(payload), BLOCK_BYTES))
    # Opus marks the *input* rate; libopus only ever produces 48 kHz, and asking it
    # for anything else fails with OPUS_BAD_ARG (observed: a 32000 Hz descriptor).
    lib = load_opus()
    pcm, channels, counts, decoded_packets, _last, _first = decode_packets(
        lib, payload, 48000)
    seconds = len(pcm) / (2 * channels) / 48000
    print(f"packets {packets:,} (decoded {decoded_packets:,})  {len(pcm):,} B PCM  "
          f"{channels} ch  {seconds:.2f} s  total {counts[-1]:,} samples")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(args.output), "wb") as handle:
            handle.setnchannels(channels)
            handle.setsampwidth(2)
            handle.setframerate(48000)
            handle.writeframes(pcm)
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
