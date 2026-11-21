# Textures

Texture dictionaries are descriptor-backed. The descriptor bounds, names, and
dimensions validate; the pixel codec and mip/tile layout do not yet.

## Descriptor model

```mermaid
classDiagram
    class TextureDictionary {
        +record_offset: u64
        +textures: List~Texture~
        +manifest: manifest.tsv
    }
    class Texture {
        +name_hash: u32
        +width: u16
        +height: u16
        +format: u16
        +mips: u8
        +graphics_pointer: u64
        +stored_bytes: u32
    }
    class GraphicsBuffer {
        +blocks: u32
        +stride: u16
        +kind: u16
        +flags: u64
        +pointer: u64
        +bounds: count × stride
    }
    class Format {
        <<enumeration>>
        FMT_0x4D
        FMT_0x62
    }
    TextureDictionary "1" *-- "0..*" Texture
    Texture "1" --> "1" GraphicsBuffer
    Texture --> Format
```

The validated relation is:

```text
stored_bytes = blocks × stride
```

Dimensions, format code, hash, pointer, stride, and bounds agree. That is not a
pixel decode.

## Current corpus

| Item | Value |
| --- | ---: |
| valid dictionaries | 73 |
| textures | 788 |
| exported bytes | 306,008,064 |
| manifest | `output/data.rpf/textures-expanded/manifest.tsv` |
| formats | `0x4D`, `0x62` |

## Decode state

```mermaid
stateDiagram-v2
    [*] --> Descriptor
    Descriptor --> BoundsOK: blocks × stride
    BoundsOK --> TopMipCandidate: choose offset/tile
    TopMipCandidate --> Plausible: spinner renders
    TopMipCandidate --> Incoherent: HUD holdouts
    Plausible --> Verified: still need a second control
    Incoherent --> Open
    Verified --> [*]
```

## Top-mip experiment

```mermaid
sequenceDiagram
    autonumber
    participant T as texture_decode.py
    participant D as descriptor
    participant B as stored bytes
    participant P as PNG samples

    T->>D: read dimensions/format/pointer/stride
    T->>B: select top-mip offset and tile
    T->>T: decode BC1/BC3 candidate
    T->>P: write sample PNG
    Note over T,P: spinner @0x800 tile4 is plausible
    Note over T,P: hud_i8d6/hud_i689 remain incoherent
```

## Open questions

- What are the actual top-mip offset and mip order?
- What is the row pitch for formats `0x4D` and `0x62`?
- Is the tile order 4×4 blocks, 16×16 pixels, or another layout?
- Which codec is used by `0x62`?
- Can a second independent texture verify the spinner candidate?

!!! warning "Not verified"
    Only `loading_screen_spinner_i1` renders plausibly. No texture conversion
    is labelled verified, and the HUD holdouts fail under the tested layouts.
