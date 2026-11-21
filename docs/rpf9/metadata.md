# Metadata regions

The metadata wall is the boundary between “the archive can be partitioned” and
“the archive index can be decoded.” The bytes are bounded, but Front A, Front B,
and the trailer are not plaintext.

## Region contract

```mermaid
classDiagram
    class Header {
        +magic: 9FPR
        +front_end: u32
        +front_block_start: u32
        +trailer_bytes: u32
        +word_24: u32
    }
    class FrontA {
        +start: 0x60
        +end: front_block_start
        +size_multiple: 16
    }
    class FrontB {
        +start: front_block_start
        +end: front_end
        +size_multiple: 16
    }
    class Trailer {
        +start: pack_end - trailer_bytes
        +end: pack_end
        +size_multiple: 16
        +behavior: CBC-like
    }
    Header "1" *-- "1" FrontA
    Header "1" *-- "1" FrontB
    Header "1" *-- "1" Trailer
```

| Region | Bounds | Observed property | Status |
| --- | --- | --- | --- |
| Front A | `0x60 .. word_08` | 16-byte multiple; no shared blocks across controls | cipher open |
| Front B | `word_08 .. word_04` | 32 bytes at N=2, 48 at N=4; large mode `align16(12(N+1))` | size model only |
| Trailer | `end - word_0c .. end` | CBC-like repeated blocks; no key | cipher open |

## Size model

For the small controls, the residual closes on `align16(10N)`. The large
localization mode uses `align16(12N)` or `align16(12(N+1))`. The discriminating
counts are both `N mod 4 = 0`, so the 12-byte-row, pad, and header/sentinel
rules coincide. A same-mode sample with `N mod 4 = 1` or `2` is still needed.

```mermaid
flowchart TD
    N[N entries] --> M{mode}
    M -- small --> A10["align16(10N)"]
    M -- large localization --> A12["align16(12N) or align16(12(N+1))"]
    A10 --> C{all controls fit?}
    A12 --> C
    C -- yes --> S[size table measured]
    C -- no --> O[open]
    S --> W[no further blind scans]
```

## Evidence state

```mermaid
stateDiagram-v2
    [*] --> Bounded
    Bounded --> PlaintextTest
    PlaintextTest --> Bounded: no plaintext record
    Bounded --> CipherTest
    CipherTest --> Bounded: no key or prefix
    Bounded --> SizeModel
    SizeModel --> Bounded: N mod 4 = 0 ambiguity
    Bounded --> Parked: need independent framing/key/field
    Parked --> [*]
```

## Attempt sequence

```mermaid
sequenceDiagram
    autonumber
    participant A as Analyst
    participant F as Front A/B
    participant T as Trailer
    participant C as Control packs

    A->>F: compare three language controls
    F-->>A: no shared prefix, suffix, or aligned block
    A->>T: group repeated blocks
    T-->>A: CBC-like, shared predecessor, no key
    A->>C: test 10N / 12N size laws
    C-->>A: measured relation, but N mod 4 = 0
    A->>A: park blind scans
```

!!! warning "Do not scan blindly"
    The project has stopped unconstrained Front A scans. Reopen only with
    independent framing, key material, a decoded field, or a new same-mode
    sample that breaks the `N mod 4` ambiguity.
