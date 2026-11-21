# Script workstream investigation (append-only)

## 2026-11-20: Array header type hashes and `vector3`

The 48-byte array header has a usable element type hash at `+0x28`. For the
vector arrays it is `0xc92cdeca`, which is the exact JOAAT of the lowercase type
name `vector3` (`tools/type_tags.py`). This is the first array field matched to
an independent name, and it confirms that `+0x28` is a type hash rather than a
record instance name.

Header fields observed on count-valid arrays:

| Offset | Meaning | Evidence |
| ---: | --- | --- |
| `+0x08` | constant `0x14` | all sampled arrays |
| `+0x10` | used count | equals `+0x14` in sampled arrays |
| `+0x14` | used count | matches vector3 entry count |
| `+0x18` | element stride | 8, 12, 16, or 48 |
| `+0x28` | element type hash | `0xc92cdeca` = `vector3` |

The body is `count * stride`; the record is 16-byte aligned, so short arrays can
end in zero padding. A 64-byte record with `stride=8` and `count=1` therefore
has one 8-byte entry plus 8 bytes of padding, not two entries.

Tagged array populations:

| Type tag | Arrays | Stride | Count | Entry observation |
| --- | ---: | ---: | ---: | --- |
| `0xc92cdeca` | 82 | 16 | 17, 21, ... | three floats plus zero pad; 12 arrays are planar (`y=0`) |
| `0x8f18aff0` | 436 | 8 | 1 | one two-float entry plus zero pad |
| `0xb1ee00d0` | 20 | 48 | 0 | empty 48-byte-element array |
| `0x2ff4ac04` | 4 | 12 | 2 | two packed three-float entries |
| `0xc4e5502a` | 46 | 8 | 0 | empty array; tag also labels property nodes |

The 82 vector3 arrays have no named ancestor within 16 pointer hops. Their
chains end at anonymous 32-byte and 96/176-byte nodes, often sharing a parent
(for example 1814, 1893, and 2126), so their semantic role (point list, curve,
bounds, or other geometry) is not yet named. The other four type tags do not
match the current JOAAT dictionary.

Tools:

```sh
python3 tools/value_entries.py script.rpf
python3 tools/value_array_context.py script.rpf
python3 tools/type_tags.py script.rpf
```

The 82 `vector3` arrays collapse to 38 unique roots. Their root classes are
`0x0` (58 arrays), `0x1` (5), `0x2` (7), `0x3` (1), `0x5` (4), `0x6` (5), and
`0x8` (2). All roots carry type `0xd72178e2`; none is a `0xffff` vehicle-like
root. The root IDs do not match the JOAAT, XML, or data bone-name dictionaries.
The arrays are therefore per-object point lists on anonymous roots, not a
class-0 layout registry. `tools/value_array_context.py` prints the root ID,
class, type, and chain.

## 2026-11-20: Generic array header decode

Validating the header as `used = +0x14`, `stride = +0x18`, `type = +0x28`, with
`used * stride <= size - 48` and less than 16 bytes of alignment padding, finds
7,894 arrays. This replaces the earlier assumption that every value array has
16-byte entries.

| Type tag | Stride | Arrays | Entries | Observation |
| --- | ---: | ---: | ---: | --- |
| `0x1ebb416b` | 48 | 3,043 | 15,732 | vec3 plus zeros plus a u32 at `+0x20`; 44 class-0 roots |
| `0x8f18aff0` | 8 | 2,491 | 7,630 | u32 hash plus f32; 252 unique hashes |
| `0xb066759f` | 32 | 1,935 | 4,365 | eight words, often one zero and one nonzero entry |
| `0xb1ee00d0` | 48 | 166 | 294 | zeros, vec3 at `+0x10`, u32 at `+0x20` |
| `0xc92cdeca` | 16 | 82 | 2,605 | `vector3`; three floats plus pad |
| `0x0000000f` | 4 | 93 | 1,646 | single floats |
| `0x2ff4ac04` | 12 | 4 | 6 | three packed floats |

The `0x1ebb416b` entries are not 3x4 matrices. A typical entry is 12 bytes of
vec3, 20 zero bytes, a u32 at `+0x20`, and 12 zero bytes. The u32 values are 141
distinct IDs of the form `[high:8][index:8]` with index 0..49 and high bytes 0,
1, and 2. Per root, 19 to 34 of the 50 indices occur; root 0 has 102 arrays and
23 indices. The class-0 chain tag `0x1ebb416b` therefore labels a 48-byte
indexed transform/value entry, not a matrix block. The exact high-byte and
index semantics remain open.

The `0x8f18aff0` pairs are `(u32 hash, f32)`; none of the 252 hashes matches the
3,212-name data bone corpus. `0xb066759f` and `0xb1ee00d0` need the same
field-level treatment. `tools/array_types.py` performs the generic decode;
`tools/value_array_context.py` now accepts any stride and prints root class and
type.

The `0x1ebb416b` u32 field has a second regularity: entries pair by low index
and high byte. Of 3,043 arrays, 2,208 contain at least one `(high=1, high=2)`
pair for the same index (4,650 pairs total). The paired vectors differ by
0 to 3.18 units; the median is 0.065 and 216 pairs are identical. This is
consistent with paired endpoints, two transform layers, or two sides, but the
current evidence does not distinguish those meanings. No skeleton graph is
claimed. `tools/transform_pairs.py` reports the pairing and distance
distribution.

## 2026-11-20: Class-0 bone table

The 44 class-0 roots with `0x1ebb416b` point arrays each have one
`0x5387a04e` table. The hierarchy is:

`class-0 root` (class 0, type `0xb0399a69`) -> `0x35e28de` node ->
`0x5387a04e` table -> `0x6503b274` bone node -> `0x1ebb416b` point array.

There are 44 tables, 3,043 entries, and exactly 3,043 point arrays. A table
entry is 16 bytes: a name hash, zero, a tagged pointer, and `0x71717171`. Every
table target has type `0x6503b274` and points to a `0x1ebb416b` array. Table
sizes vary from 4 to 155 entries; roots 0 and 209 have 102, and one root has 96.
The table hash namespace has 612 values shared across roots; the
`0x8f18aff0` pair namespace has 252 values, 57 of which overlap the table
hashes. No table hash matches JOAAT, CRC32, FNV-1a, FNV-1, djb2, or sdbm over
381k XML, bone, and resource-name candidates.

`tools/bone_table.py` flattens the hierarchy and writes
`handoff/script-bones.tsv` with root, table, bone hash, target, point count, and
first point.
