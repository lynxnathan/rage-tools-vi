"""Minimal end-to-end pipeline: RDNA2 ISA bytes in, SPIR-V module out.

This is the M0 unit test, deliberately small. It does three things and nothing
else:

  1. Parse AMD's machine-readable ISA XML (MIT) into encoding rules.
  2. Walk a byte range as a GFX10 instruction stream, one instruction at a time,
     recording offset, size, encoding and mnemonic. Nothing is guessed: the word
     must match an encoding's identifier mask exactly, and an instruction that
     carries an inline literal consumes the extra word.
  3. Emit one valid SPIR-V 1.5 module per input. The module carries the decoded
     stream as line-table entries (one `OpLine` per instruction, line = index,
     column = size) and a trivial compute entry point. It is not a translation
     yet; it is the carrier that later milestones replace `OpLine` with real
     instructions.

Usage:

    python3 rdna2-spirv/tools/isa2spv.py --spec cache/rdna2/specs/amdgpu_isa_rdna2.xml \
        --input cache/rdna2/corpus --out cache/rdna2/spv --report cache/rdna2/report.tsv

Every failure is recorded with its offset and word; the exit status is 0 when at
least one blob decoded and every emitted module validated, 1 otherwise.
"""

import argparse
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# spec
# --------------------------------------------------------------------------

@dataclass
class Encoding:
    name: str
    bits: int
    mask: int
    ids: set
    order: int


def _bits(text, radix):
    return int(text, int(radix)) if radix.isdigit() else int(text, 2)


def load_spec(path):
    root = ET.parse(path).getroot()
    encodings = {}
    for element in root.findall(".//Encodings/Encoding"):
        name = element.findtext("EncodingName")
        bits = int(element.findtext("BitCount"))
        mask_element = element.find("EncodingIdentifierMask")
        mask = int(mask_element.text, 2)
        ids = {int(i.text, 2) for i in element.findall(".//EncodingIdentifier")}
        encodings[name] = Encoding(name, bits, mask, ids, int(element.get("Order", "0")))

    # instruction name and literal flag, keyed by (encoding, opcode)
    table = {}
    for element in root.findall(".//Instructions/Instruction"):
        name = element.findtext("InstructionName")
        flags = element.find("InstructionFlags")
        branch = flags is not None and flags.findtext("IsBranch") == "TRUE"
        terminal = flags is not None and flags.findtext("IsProgramTerminator") == "TRUE"
        literal = any(
            "LITERAL" in (operand.findtext("FieldName") or "").upper()
            or "LITERAL" in (operand.findtext("OperandType") or "").upper()
            for operand in element.findall(".//Operand")
        )
        for encoding in element.findall(".//InstructionEncoding"):
            key = (encoding.findtext("EncodingName"), int(encoding.findtext("Opcode")))
            table[key] = (name, literal, branch, terminal)
    return encodings, table


SKIP_VARIANTS = ("INST_LITERAL", "NSA", "SDWA", "DPP", "SDST_ENC")


def opcode_field(encoding):
    """(shift, width) of the opcode bits.

    The mask in the XML marks bits fixed by the instruction *format*, which is
    not the opcode field: SOPP fixes bits 31:16 in the mask while the opcode
    lives at 21:16. The reliable source is the identifier list itself: the bits
    that differ between identifiers are exactly the opcode field.
    """
    ids = sorted(encoding.ids)
    if len(ids) < 2:
        return None
    differing = 0
    for value in ids:
        differing |= value ^ ids[0]
    differing &= 0xFFFFFFFF
    if differing == 0:
        return None
    shift = (differing & -differing).bit_length() - 1
    width = bin(differing).count("1")
    if differing != ((1 << width) - 1) << shift:
        return None                      # opcode bits are not contiguous
    return shift, width


def build_decoder(encodings, table):
    """Return (mask_tables, ordered_masks).

    `mask_tables[mask][word & mask]` yields the instruction for that word, and
    `ordered_masks` is the precedence order (the XML's Encoding/@Order). The XML
    lists one identifier per opcode, and the mask marks the bits the format
    fixes, so matching is `word & mask == identifier`.
    """
    rules = []
    for encoding in encodings.values():
        if any(tag in encoding.name for tag in SKIP_VARIANTS):
            continue
        field = opcode_field(encoding)
        if field is None:
            continue
        shift, width = field
        opcodes = {}
        for key_encoding, instruction in table.items():
            if key_encoding[0] == encoding.name:
                opcodes[key_encoding[1] & ((1 << width) - 1)] = instruction
        if not opcodes:
            continue
        for identifier in encoding.ids:
            opcode = (identifier >> shift) & ((1 << width) - 1)
            if opcode not in opcodes:
                continue
            name, literal, branch, terminal = opcodes[opcode]
            rules.append((encoding.order, encoding.mask & 0xFFFFFFFF, identifier,
                          encoding.bits // 8, encoding.name, name,
                          literal, branch, terminal))
    rules.sort(key=lambda rule: rule[0])
    mask_tables = {}
    for order, mask, value, size, encoding, name, literal, branch, terminal in rules:
        mask_tables.setdefault(mask, {}).setdefault(
            value, (order, size, encoding, name, literal, branch, terminal))
    ordered = sorted(mask_tables.items(),
                     key=lambda item: min(hit[0] for hit in item[1].values()))
    return mask_tables, ordered


# --------------------------------------------------------------------------
# decode
# --------------------------------------------------------------------------

@dataclass
class Insn:
    offset: int
    size: int
    encoding: str
    mnemonic: str
    branch: bool
    terminal: bool


def decode_one(word, decoder):
    for mask, table in decoder[1]:
        hit = table.get(word & mask)
        if hit is not None:
            return hit
    return None


def decode(data, decoder, start=0, limit=None):
    """Return (instructions, error) where error is (offset, word, reason)."""
    out = []
    offset = start
    end = len(data) if limit is None else min(len(data), start + limit)
    while offset + 4 <= end:
        word = struct.unpack_from("<I", data, offset)[0]
        hit = decode_one(word, decoder)
        if hit is None:
            return out, (offset, word, "no encoding match")
        order, size, encoding, name, literal, branch, terminal = hit
        if literal and offset + 8 <= end:
            # A literal is a trailing 32-bit word, present only when a source
            # operand selects it. Keep the 4-byte form when the next word is
            # itself a valid instruction.
            following = struct.unpack_from("<I", data, offset + 4)[0]
            if decode_one(following, decoder) is None:
                size += 4
        if offset + size > end:
            return out, (offset, word, "truncated")
        out.append(Insn(offset, size, encoding, name, branch, terminal))
        offset += size
    if offset != end:
        return out, (offset, 0, f"{end - offset} trailing bytes")
    return out, None


def carve(data, decoder, minimum=16, stride=4):
    """Maximal decodable runs, the generic container adapter.

    Scans forward for the first offset at which a stream of at least `minimum`
    instructions decodes without a stop, then continues after that run. No
    knowledge of any container format is used.
    """
    runs = []
    position = 0
    while position + 4 <= len(data):
        insns, error = decode(data, decoder, start=position)
        if len(insns) >= minimum:
            runs.append((position, insns))
            position += sum(insn.size for insn in insns)
        else:
            position += stride
    return runs


# --------------------------------------------------------------------------
# SPIR-V
# --------------------------------------------------------------------------

SPV_MAGIC = 0x07230203
SPV_VERSION = 0x00010500
OP_CAPABILITY, OP_STRING, OP_EXTENSION = 17, 7, 10
OP_MEMORY_MODEL, OP_ENTRY_POINT, OP_EXECUTION_MODE, OP_NAME = 14, 15, 16, 5
OP_TYPE_VOID, OP_TYPE_FUNCTION = 19, 33
OP_FUNCTION, OP_FUNCTION_END, OP_LABEL, OP_RETURN, OP_LINE = 54, 56, 248, 253, 8


class Module:
    def __init__(self):
        self.words = []
        self.bound = 1

    def new_id(self):
        value = self.bound
        self.bound += 1
        return value

    def op(self, opcode, *operands):
        self.words.append(((len(operands) + 1) << 16) | opcode)
        self.words.extend(operands)

    def string(self, text):
        raw = text.encode()
        padded = raw + b"\0"
        while len(padded) % 4:
            padded += b"\0"
        return struct.unpack(f"<{len(padded) // 4}I", padded)


def emit_spirv(name, insns, source_name="rdna2"):
    module = Module()
    void = module.new_id()
    function_type = module.new_id()
    main = module.new_id()
    label = module.new_id()
    file_id = module.new_id()
    source = module.new_id()

    module.op(OP_CAPABILITY, 1)                 # Shader
    module.op(OP_MEMORY_MODEL, 0, 1)            # Logical GLSL450
    module.op(OP_ENTRY_POINT, 5, main, *module.string("main"))
    module.op(OP_EXECUTION_MODE, main, 17, 1, 1, 1)  # LocalSize 1 1 1
    module.op(OP_STRING, file_id, *module.string(name))
    module.op(OP_STRING, source, *module.string(f"{len(insns)} instructions"))
    module.op(OP_TYPE_VOID, void)
    module.op(OP_TYPE_FUNCTION, function_type, void)
    module.op(OP_FUNCTION, void, main, 0, function_type)
    module.op(OP_LABEL, label)
    for index, insn in enumerate(insns):
        module.op(OP_LINE, file_id, index, insn.size)
    module.op(OP_RETURN)
    module.op(OP_FUNCTION_END)

    header = [SPV_MAGIC, SPV_VERSION, 0, module.bound, 0]
    return struct.pack(f"<{len(header) + len(module.words)}I",
                       *header, *module.words)


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True,
                        help="a .bin file or a directory of them")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--carve", action="store_true",
                        help="treat input as a container and carve decodable runs")
    parser.add_argument("--minimum", type=int, default=16,
                        help="minimum instructions in a carved run (default 16)")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    encodings, table = load_spec(args.spec)
    decoder = build_decoder(encodings, table)
    print(f"spec: {len(encodings)} encodings, {len(table)} instruction encodings, "
          f"{sum(len(t) for t in decoder[0].values())} identifiers, "
          f"{len(decoder[1])} mask tables")

    files = sorted(args.input.glob("*.bin")) if args.input.is_dir() else [args.input]
    if args.limit:
        files = files[:args.limit]
    args.out.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in files:
        data = path.read_bytes()
        if args.carve:
            units = carve(data, decoder, minimum=args.minimum)
        else:
            insns, _ = decode(data, decoder)
            units = [(0, insns)] if insns else []
        for offset, insns in units:
            label = f"{path.stem}_{offset:06x}"
            blob = emit_spirv(label, insns)
            (args.out / f"{label}.spv").write_bytes(blob)
            rows.append((path.name, offset, sum(i.size for i in insns),
                         len(insns), len(blob)))

    covered = sum(row[2] for row in rows)
    total = sum(p.stat().st_size for p in files)
    print(f"blobs {len(files)}: units {len(rows)}, instructions "
          f"{sum(row[3] for row in rows):,}, ISA bytes {covered:,} of {total:,} "
          f"({covered / total:.1%}), SPIR-V bytes {sum(row[4] for row in rows):,}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w") as handle:
            handle.write("blob\toffset\tisa_bytes\tinstructions\tspv_bytes\n")
            for row in rows:
                handle.write("\t".join(str(cell) for cell in row) + "\n")
        print(f"report: {args.report}")
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
