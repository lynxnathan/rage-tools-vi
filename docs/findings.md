# What we found

A summary of the verified results, written for a reader who has not followed the
journal. Each claim links to the page or artifact that proves it; the append-only
evidence lives in `investigation.md`.

## The container

RPF9 is a 0x60-byte header followed by three metadata regions and a payload:

| Region | Bounds | State |
| --- | --- | --- |
| Header | `0x00..0x60` | mapped, 24 words |
| Front A | `0x60..+0x08` | **masked**; holds names and paths |
| Front B | `+0x08..+0x04` | **masked**; the entry table |
| Payload | Front B end .. trailer | zlib chains, opaque spans, zero runs |
| Trailer | `end - +0x0c .. end` | **masked**; CBC-like, pack-independent chain |

The header fields are known well enough to predict sizes without decoding:
`+0x0c` is the trailer length in all 4,373 headers censused, and Front B is
`align16(9N)` or `align16(10N)` exactly — selected by a count-driven tag — for
all 2,908 mode-family-1 headers. Every payload stream is located by scanning and
checksum verification, not by the table.

## Coverage

All 22 source archives are indexed: **4,415,850 ranges / 161.3 GB stored /
365.0 GB decoded**, and every index tiles its archive exactly, with no gap and no
overlap. Six archives plus `levels` carry bulk extraction manifests covering
2,190,635 zlib ranges; each extraction is SHA-256 verified.

The unclassified layer is **closed**: every large span is media. 38.1 GB of AWC
audio, 13.4 GB of Bink/Bink2 video, ~1.2 GB of fragments. There is no unexplained
game payload left in it.

## Entry identity from the payload

The index table is masked, so entries are identified from the payload instead:

| Archive | Unit | Packs verified | Entries |
| --- | --- | ---: | ---: |
| `core_bvh4` | pairs | **1,253 / 1,261** | 109,301 |
| `navmeshes` | chains | 14 / 28 | 23,530 |
| `packs` | pairs | 20 / 59 | 15,983 |
| `levels` | pairs | 728 / 2,044 | 29,117 |
| `anim` | chains | 125 / 235 | 5,826 |
| `data` | chains | 16 / 40 | 2,063 |
| `textures` | pairs | 17 / 20 | 1,326 |

**188,298 entries** with exact, payload-derived boundaries and an independent
check against the declared count, across **14 archives**; the table above shows the
largest. Every pack contributed only when its entry count verified exactly, and the
full per-archive table is [the corpus pass](extraction/corpus.md).

## Naming

Every identifier encountered is `JOAAT(lowercase name)`. That single fact turned
hash tables into readable rigs:

- **99 of 612** class-0 bone-table hashes and **21 of 252** weight hashes resolve
  through the `skel_` / `mh_` / `rb_` families (skeleton, muscle helpers, ragdoll).
- One rig is fully decoded: root `0x48dcbb01`, 34/34 bones — a two-sided
  hand/forearm rig with four three-segment finger chains.
- The 16 skeleton families carry readings: a hand rig, a genital rig, large
  animals, and a small-prop population that still holds an unnamed 330-hash
  universe.

## Audio

`audio.rpf`'s 23.5 GB of AWC containers decode to Opus, XMA2 and ACE1 impulse
responses. `story000` turned out to hold a second, larger audio archive: 9.56 GB
of AWC in a different container variant, now decoded to **196,350 Opus streams /
148.3 hours / 47.7 GB of WAV**.

## What is not solved

- Front A, Front B and the trailer are masked. The size laws are known; the
  contents are not. Four metadata questions are blocked on key material or a
  crib, not on effort.
- The remaining 330-hash universe is a vocabulary problem: the names are not in
  the corpora harvested so far.
- Packs whose entries mix shapes cannot be counted exactly; ~68 in `core_bvh4`,
  16 in `navmeshes`, 23 in `data`, 2 in `textures`.

See the [roadmap](roadmap.md) for the live list.
