#!/usr/bin/env python3 -I
"""K2 exe-side fingerprint pass over game_scarlett_master.exe (bounded, single).

Methodology mirrors tools/keyhunt/p2_fingerprint.py + p2b_broad.py (Nov-19 keyhunt)
plus the X1 brief's crypto_census requirements. Static analysis only; target path is
passed as argv[1]; windowed/mmap reads only. Everything saved to
exeK2/exe_crypto_census.json. Twin-run rule applies (run twice, sha must match).
"""
import struct, sys, os, json

EXE = sys.argv[1] if len(sys.argv) > 1 else \
    "/Volumes/1tb SSD/recomp2/GTA6.Xbox.v1.0.2.1/game_scarlett_master.exe"
OUT = "/Volumes/1tb SSD/recomp2/tools/probes-scratch/exeK2/exe_crypto_census.json"
WIN = 4 << 20  # 4 MiB windows
size = os.path.getsize(EXE)

# AES S-box computed from definition (GF(2^8) inverse + affine map) — no transcription.
def _gfmul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if a & 0x100:
            a ^= 0x11B
    return r

def _rotr(v, n):
    n %= 8
    return ((v >> n) | (v << (8 - n))) & 0xFF

def _gen_sbox(direction):
    inv = [0] * 256
    for x in range(1, 256):
        for y in range(1, 256):
            if _gfmul(x, y) == 1:
                inv[x] = y
                break
    box = []
    for x in range(256):
        v = inv[x]
        if direction == "right":
            v ^= _rotr(v, 1) ^ _rotr(v, 2) ^ _rotr(v, 3) ^ _rotr(v, 4)
        else:  # left rotations == negative shift
            v ^= _rotr(v, -1) ^ _rotr(v, -2) ^ _rotr(v, -3) ^ _rotr(v, -4)
        box.append(v ^ 0x63)
    return bytes(box)

SBOX = None
for _dirn in ("right", "left"):
    cand = _gen_sbox(_dirn)
    if cand[0] == 0x63 and cand[1] == 0x7C:
        SBOX = cand
        break
if SBOX is None:
    raise RuntimeError("computed AES S-box matched no known anchor value")
assert len(SBOX) == 256 and sorted(SBOX) == list(range(256)), "S-box not a permutation"
_inv = bytearray(256)
for _i, _v in enumerate(SBOX):
    _inv[_v] = _i
INV_SBOX = bytes(_inv)
CONST = bytes.fromhex("5f08daabecbdd40258c3516807024c24fb9f756755ef4be458785bfed8aa6989")
SHA256_K = bytes.fromhex("67e6096a43d86a61020960d2d839d1117b9dbd0a56bc64d01093bcdd")
BLAKE_SIGMA_A = bytes.fromhex("000102030405060708090a0b0c0d0e0f1020304051120607")  # row-major head variant (32B)
CHACHA_RAW = struct.pack("<4I", *[0x61707865, 0x3320646e, 0x79622d32, 0x6b206574])
CHACHA_ASCII = b"expand 32-byte t"

def dword_swap(b):  # swap each little-endian 4-byte group to big-endian
    return b"".join(b[i:i+4][::-1] for i in range(0, len(b), 4))

def qword_swap(b):
    return b"".join(b[i:i+8][::-1] for i in range(0, len(b), 8))

SIGS = {
    "CONST32_raw": CONST,
    "CONST32_rev": CONST[::-1],
    "CONST32_dwordswap": dword_swap(CONST),
    "CONST32_qwordswap": qword_swap(CONST),
    "CONST_lo16_raw": CONST[:16],
    "CONST_hi16_raw": CONST[16:],
    "aes_sbox_full": SBOX,
    "aes_sbox_first64": SBOX[:64],
    "aes_sbox_first32": SBOX[:32],
    "aes_inv_sbox_full": INV_SBOX,
    "aes_inv_sbox_first64": INV_SBOX[:64],
    "sha256_K12": SHA256_K,
    "chacha_const_raw": CHACHA_RAW,
    "chacha_const_ascii": CHACHA_ASCII,
}
FOURCC = ["KB2", "RPF", "PSIN", "RDS5", "ETPF", "RBF0", "AES", "RC4"]

# ---- PE section table ----
with open(EXE, "rb") as f:
    f.seek(0x3C); pe_off = struct.unpack("<I", f.read(4))[0]
    f.seek(pe_off + 4)
    coff = f.read(20)
    nsec, optsz = struct.unpack_from("<H", coff, 2)[0], struct.unpack_from("<H", coff, 16)[0]
    f.seek(pe_off + 24 + optsz)
    secs = []
    for _ in range(nsec):
        e = f.read(40)
        name = e[:8].rstrip(b"\x00").decode("latin1", "replace")
        vsz, va, rsz, roff = struct.unpack_from("<IIII", e, 8)
        secs.append({"name": name, "vaddr": hex(va), "vsize": hex(vsz),
                    "rawoff": hex(roff), "rawsize": hex(rsz)})
sec_by_name = {s["name"]: s for s in secs}

hits = {k: [] for k in SIGS}
fourcc_ascii = {k: [] for k in FOURCC}
fourcc_le = {k: [] for k in FOURCC}   # e.g. "RPF9"/"KB2n" LE-stored fourCC = token reversed
with open(EXE, "rb") as f:
    off = 0
    while True:
        buf = f.read(WIN)
        if not buf:
            break
        tail_len = 255
        # scan signatures in [off, off+len(buf)-tail) so overlaps can't split blobs
        span_end = max(0, len(buf) - tail_len)
        region = buf[:span_end]
        base = off
        for name, pat in SIGS.items():
            start = 0
            while len(hits[name]) < 64:
                i = region.find(pat, start)
                if i < 0:
                    break
                hits[name].append(base + i)
                start = i + 1
        for tok in FOURCC:
            tb = tok.encode()
            start = 0
            while len(fourcc_ascii[tok]) < 200:
                i = region.find(tb, start)
                if i < 0:
                    break
                fourcc_ascii[tok].append(base + i)
                start = i + 1
            lstart = 0
            lb = tb[::-1]
            while len(fourcc_le[tok]) < 200:
                j = region.find(lb, lstart)
                if j < 0:
                    break
                fourcc_le[tok].append(base + j)
                lstart = j + 1
        off += span_end

# ---- AES-NI opcode histogram over .text vs .pdata control ----
OPCODES = {
    "aesenc(66 0F 38 DC)": b"\x66\x0f\x38\xdc",
    "aesenclast(66 0F 38 DD)": b"\x66\x0f\x38\xdd",
    "aesdec(66 0F 38 DE)": b"\x66\x0f\x38\xde",
    "aesdeclast(66 0F 38 DF)": b"\x66\x0f\x38\xdf",
    "aesimc(66 0F 38 DB)": b"\x66\x0f\x38\xdb",
    "aeskeygenassist(66 0F 3A DF)": b"\x66\x0f\x3a\xdf",
}
from collections import Counter
op_counts = {"text": Counter(), "pdata": Counter()}
op_first20 = {}
with open(EXE, "rb") as f:
    for secname, tag in ((".text", "text"), (".pdata", "pdata")):
        s = sec_by_name.get(secname)
        if not s:
            continue
        roff, rsz = int(s["rawoff"], 16), int(s["rawsize"], 16)
        f.seek(roff)
        pos = 0
        while pos < rsz:
            buf = f.read(min(WIN, rsz - pos))
            if not buf:
                break
            for oname, opat in OPCODES.items():
                c = buf.count(opat)
                op_counts[tag][oname] += c
                lst = op_first20.setdefault((tag, oname), [])
                start = 0
                while len(lst) < 20:
                    i = buf.find(opat, start)
                    if i < 0:
                        break
                    lst.append(hex(pos + i))
                    start = i + 1
            pos += len(buf)

# ---- PDB path (debug dir) ----
pdb_hits = []
with open(EXE, "rb") as f:
    off = 0
    while True:
        buf = f.read(WIN)
        if not buf:
            break
        span_end = max(0, len(buf) - 255)
        region = buf[:span_end]
        i = region.find(b".pdb")
        j = region.find(b"p\x00d\x00b\x00")  # utf16le hint
        st = min(x for x in (i, j, span_end) if x >= 0)
        while st < span_end:
            # ascii context
            a = region.rfind(range_guard := None) if False else st
            lo = max(0, st - 100); hi = min(len(buf), st + 120)
            ctx_a = "".join(chr(c) if 32 <= c < 127 else "." for c in buf[lo:hi])
            try:
                ctx_u = buf[lo:hi].decode("utf-16-le", "ignore")[:110]
            except Exception:
                ctx_u = ""
            pdb_hits.append({"off": hex(off + st), "ascii_ctx": ctx_a, "utf16_ctx": ctx_u})
            if len(pdb_hits) > 12:
                break
            nxt_a = region.find(b".pdb", st + 1)
            nxt_u = region.find(b"p\x00d\x00b\x00", st + 1)
            cand = [x for x in (nxt_a, nxt_u) if x >= 0]
            if not cand:
                break
            st = min(cand)
        if len(pdb_hits) > 12:
            break
        off += span_end

report = {
    "exe": EXE, "size": size,
    "sections": secs,
    "method": {
        "window_bytes": WIN, "overlap_tail_bytes": 255,
        "max_offsets_per_sig_listed": 64, "exact_blob_search": True,
        "note": "hit offsets are raw file offsets; lists capped, counts are true-found-anywhere only within cap",
    },
    "const_search": {},
    "sig_hits": {},
    "fourcc_ascii_counts_uncapped_offsets_capped": {},
    "fourcc_le_store_counts_uncapped_offsets_capped": {},
    "aesni_histogram": {k: dict(v) for k, v in op_counts.items()},
    "aesni_first20": {f"{k[0]}/{k[1]}": v for k, v in op_first20.items()},
    "pdb_candidates": pdb_hits,
}
for k in SIGS:
    entry = {"count_found": len(hits[k]), "first_offsets_hex": [hex(o) for o in hits[k][:64]]}
    if k.startswith("CONST"):
        report["const_search"][k] = entry
    else:
        report["sig_hits"][k] = entry
for tok in FOURCC:
    report["fourcc_ascii_counts_uncapped_offsets_capped"][tok] = len(fourcc_ascii[tok])
    report["fourcc_le_store_counts_uncapped_offsets_capped"][tok] = len(fourcc_le[tok])

with open(OUT, "w") as f:
    json.dump(report, f, indent=1)

print("== CONST32 EXACT SEARCH ==")
for k, v in report["const_search"].items():
    print("  %-24s found=%d %s" % (k, v["count_found"], v["first_offsets_hex"][:8]))
print("== CRYPTO SIGS ==")
for k, v in report["sig_hits"].items():
    print("  %-24s found=%d %s" % (k, v["count_found"], v["first_offsets_hex"][:5]))
print("== FOURCC (offset-capped ~200) ==")
print("  ascii:", {k: v for k, v in report["fourcc_ascii_counts_uncapped_offsets_capped"].items()})
print("  le-store:", {k: v for k, v in report["fourcc_le_store_counts_uncapped_offsets_capped"].items()})
print("== AES-NI ==")
print("  .text :", dict(op_counts["text"]))
print("  .pdata:", dict(op_counts["pdata"]))
print("== PDB candidates ==")
for p in pdb_hits[:6]:
    print("  ", p["off"], "|", (p["ascii_ctx"] or p["utf16_ctx"])[:90])
print("\nsaved:", OUT)
