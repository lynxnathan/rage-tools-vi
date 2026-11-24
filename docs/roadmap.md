# Roadmap

The roadmap is a living section. `plan.md` is the canonical live check/todo
list and this page is the visual projection; evidence lives in
`investigation.md`.

## Milestones

```mermaid
gantt
    title Rage Tools VI milestones
    dateFormat  YYYY-MM-DD
    axisFormat  %m-%d
    section Verified
    RPF9 partition and zlib gates :done, 2026-11-20, 1d
    Script object graph           :done, 2026-11-20, 1d
    Audio complete (Opus/XMA2/ACE1) :done, 2026-11-21, 1d
    Full output rebuild           :done, 2026-11-21, 1d
    Script metadata chain from writer :done, 2026-11-23, 1d
    PSIN field order corrected    :done, 2026-11-23, 1d
    Buffer A layout from the binary :done, 2026-11-23, 1d
    section Active
    Buffer A section roles        :active, 2026-11-23, 5d
    Stream Read (+0x60) identity  :2026-11-23, 4d
    Bone hash names / geometry    :2026-11-24, 4d
    Remaining typed arrays        :2026-11-24, 4d
    section Blocked
    Texture codec and top mip     :crit, 2026-11-20, 10d
    section Next
    Entry → payload range proof   :2026-11-26, 7d
    Full archive extraction       :2026-12-03, 10d
```

## State

```mermaid
stateDiagram-v2
    [*] --> Partitioned
    Partitioned --> ObjectGraph: 42-stream object
    ObjectGraph --> TypedArrays: header decode
    TypedArrays --> BoneTable: class-0 hierarchy
    BoneTable --> Naming: hash/name alignment
    Naming --> Milestone: record predicts payload range
    Milestone --> FullExtraction
    Partitioned --> MetadataLayout: buffer A arena formula
    MetadataLayout --> SectionRoles: 654/654 headers fit
    FullExtraction --> [*]
```

## Current work

| Priority | Task | Evidence | Blocker |
| --- | --- | --- | --- |
| 1 | Identify buffer A's five sections | arena formula, 654/654 fit | section semantics |
| 2 | Read the stream's `Read` (`+0x60`) | archive copies buffers verbatim | class identity |
| 3 | Name or align the 612 bone hashes | `handoff/script-bones.tsv` | hash namespace |
| 4 | Decode remaining typed arrays | `0xb066759f`, `0xb1ee00d0` | field semantics |
| 5 | Texture top-mip verification | spinner + HUD holdouts | codec/pitch/tile |
| 6 | `CHKS` trailer tag | size field verified 60/60 | hash function outside our set |

## Done

- [x] Map `common.rpf` stored ranges and payload groups.
- [x] Verify the 42-stream object, PSIN records, XML, and story control.
- [x] Confirm metadata region sizes and header invariants.
- [x] Map the `LSNS` tables: 16-byte records, framing valid on 1,012/1,012 records.
- [x] Resolve the 64 KiB continuation rule.
- [x] Name 306 of 483 object roots with JOAAT.
- [x] Decode typed array headers and the `vector3` type tag.
- [x] Recover the script metadata chunk chain from the writer in the executable.
- [x] Correct the PSIN row field order and rebuild the affected artifacts.
- [x] Derive buffer A's arena layout from the binary; it fits 654/654 headers.
- [x] Flatten the 44 class-0 bone tables and 3,043 bones.
- [x] Rebuild all six verified archive extractions after a clean output wipe.
- [x] Decode 151 AWC codec-`0x05` streams as XMA2 WAV.
- [x] Decode 2,081 AWC codec-`0x0B` streams as untrimmed Opus WAV.
- [x] Decode 73 AWC codec-`0x02` streams as ACE1 impulse responses.

## Parked

- The 331,728-byte blob: verified by hash, but it is neither a single indexed range
  nor a single decoded stream, so its origin is not re-derivable from the current
  index.
- What populates the 16-bit id dictionary (`0xb7076b6245d35fb5`): accessors and the
  probe loop are read, no initialiser has been seen.
- Format `0x62` texture codec until a verified control exists.
