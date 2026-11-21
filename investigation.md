# RPF9 extraction investigation

> Current roadmap and state: [plan.md](plan.md). This file is an append-only
> journal; add new evidence at the end.

## Goal and current status

The goal is to enumerate every archive entry, locate its stored bytes, and extract it with the correct decoding. Filename recovery can follow. Entry numbers or hashes are sufficient to verify complete extraction.

Partial extraction works by scanning for complete zlib streams and checking their checksums. The archive entry table remains undecoded. We have yet to establish an entry count, an indexed payload range, or a filename or name hash read from an RPF9 entry.

The tests below used the workspace copies of [script.rpf](script.rpf), [common.rpf](common.rpf), and [story000_bvh4.rpf](story000_bvh4.rpf). These archives and the extracted output live in the original checkout. From a sibling worktree, pass their paths in the original checkout to the CLI.

## RPF8 baseline

The RDR2 RPF8 reader reads a 16-byte header, a 256-byte RSA signature, and a fixed-width entry table starting at 0x110. The header supplies the entry count and a decryption tag. Each decoded 24-byte entry gives the reader a path hash, an extension ID, encryption flags, a stored offset and size in 16-byte units, a codec, and either a decoded size or resource sizing information. [Swage reader](https://github.com/0x1F9F1/Swage/blob/master/src/games/rage/rpf8.cpp) · [Swage entry definitions](https://github.com/0x1F9F1/Swage/blob/master/src/games/rage/rpf8.h)

RPF8 tools resolve hashes with separate name dictionaries. Swage imports text lists of known and possible names. OpenRAGE scans a local game install for candidate strings and matches them to hashes. RPF9 may use a different naming scheme. [Swage name loading](https://github.com/0x1F9F1/Swage/blob/201320d61ae04909f01af247c41f864a9174b691/src/explorer/explorer.cpp#L1032-L1044) · [OpenRAGE name recovery](https://two-play.github.io/openrage/rdr2/#2-find-the-file-names)

I ran VIRUXE's rpf-archive 0.10.0 and upstream revision edd7758. Both listed and extracted a synthetic RPF7 control and rejected script.rpf with unknown archive magic 0x52504639. Applying the RPF8 layout directly to the RPF9 bytes yielded 338 out-of-bounds ranges out of 608 putative records. That test establishes that the unmodified reader cannot extract this sample. [Rust library](https://github.com/VIRUXE/rpf-archive-rs)

## Observed RPF9 layout

Ranges below use inclusive starts and exclusive ends. Header field roles other than the magic remain interpretations of the samples.

| Relative offset | Observation |
| --- | --- |
| +0x00 | Magic bytes 39 46 50 52, or 0x52504639 as a little-endian integer |
| +0x04 | Tracks the end of the front region |
| +0x08 | Falls within the front region and marks a candidate metadata boundary |
| +0x0c | Matches the sizes of the candidate trailers in both samples |
| +0x24 | Count-like field. Values include 2, 418, and 1,012. The 1,012 value equals the number of recovered PSIN records in one embedded pack. |
| +0x40 to +0x60 | The same 32 bytes recur in the observed headers |

| Archive or embedded pack | Front region | Candidate front block | Candidate trailer |
| --- | --- | --- | --- |
| common.rpf | 0x0 to 0x9580 | 0x8520 to 0x9580 | 0x652000 to 0x655a10 |
| script.rpf root | 0x0 to 0x260 | 0x240 to 0x260 | 0x4282b0 to 0x428330 |
| script.rpf embedded pack at 0x1000 | 0x1000 to 0x1480 | 0x1460 to 0x1480 | 0xc3b50 to 0xc3b90 |
| script.rpf embedded pack at 0xc4000 | 0xc4000 to 0xd5f10 | 0xd2f90 to 0xd5f10 | 0x422000 to 0x4282b0 |

The two packs with the count-like value 2 have candidate trailers of 64 and 128 bytes. Their trailers share an identical first 16-byte block. The block encoding is unknown.

The small embedded pack contains one opaque span from 0x2010 to 0x52fe0 and a contiguous chain of 42 verified zlib streams from 0x53000 to 0xc3b45. Tests for plain integer fields and an RPF8-style packed offset and size found no match for those payload boundaries in its candidate front block or trailer. Checks against the larger embedded pack also failed to recover a usable sequence of offsets.

## script.rpf payloads

- A scan found 1,057 complete 16-byte-aligned zlib streams, including 1,012 beginning with PSIN.
- Each of the three PSIN records starting at 0xe7000, 0x3e5000, and 0x417000 continues in a second zlib stream. The first stream in each decodes to 64 KiB. The reassembled records are 99,536, 119,296, and 119,920 bytes. The CLI checks both zlib streams, the intervening zero bytes, the decoded section boundaries, and the total length recorded in the final CHKS section.
- The recurring section sequence is PSIN, LSCH, LENM, LSNS, LGID, LRSC, and CHKS. All 1,012 PSIN records were independently checked against the section parser.
- All LSNS bodies have a 12-byte header containing little-endian values 1, 257, and the body length. The body length is a multiple of 16 in every record. Across 869 distinct bodies, repeated 16-byte blocks appeared only with the same preceding prefix. This is consistent with chained block encryption. The cipher and body contents are unknown.
- The UTF-8 scan found readable section tags and incidental printable fragments. It found no recognizable file paths, filenames, or messages in the inflated streams.
- The RDR2 decompiler's header parser passed a synthetic RSC8 control and found no matching script header in the 1,057 inflated streams or in a concatenation of 42 consecutive streams. An embedded-header scan also found no matching older code-page and script-name pointer layout. Script bytecode remains unidentified. [RDR2 PC script decompiler](https://github.com/maybegreat48/GTA-V-Script-Decompiler) · [RASM PC and console header definitions](https://github.com/NativeFunction/RASM/blob/master/RASM/Include/Game/GameHeaders.h)

## common.rpf payloads

- The verified byte map includes 954 zlib streams, 277 candidate zlib chains, and 117 unclassified ranges totaling 210,272 bytes. The chain heuristic requires a preceding 64 KiB decoded chunk, a next stream at the next 16-byte boundary, and zero bytes in the gap. Candidate chains still need independent validation as archive entries.
- All 259 complete XML documents, including 79 using multiple streams, were written to [output/common.rpf](output/common.rpf) using hexadecimal offsets as filenames. Each was matched back to its decoded chain byte-for-byte. Some additional zlib chains contain partial XML.
- Seven XML document IDs match basenames referenced by another document. For example, the document at 0xb000 identifies itself as core_binks and the content manifest references changesets/ccs_core_binks.meta. These are inferred associations from the payloads. Matching candidate names and hashes against the undecoded front and trailer blocks yielded no archive-entry name. [Extracted core_binks](output/common.rpf/00b000.xml) · [Content manifest](output/common.rpf/014000.xml)
- There is an HMAP heightmap at 0x12b000. All 164 rows and both planes of its 144 × 164 grid agreed with the older heightmap layout. The level manifest references common:/data/levels/americas/heightmap.dat under WORLD_HEIGHTMAP_FILE. This is a strong candidate name. [Level manifest](output/common.rpf/129000.xml) · [CodeWalker heightmap reader](https://github.com/dexyfex/CodeWalker/blob/master/CodeWalker.Core/GameFiles/FileTypes/HeightmapFile.cs)
- The SPS1 payload at 0x650000 contains 858 records, each with a length-prefixed .sps path, a shader name, and an unidentified byte. The streams at 0x64e000 and 0x64f1c0 contain lists of 965 and 22 .fx names. Those names belong to the listed items. The archive filenames of the lists and index are unknown.
- A multi-stream visual configuration table starts at 0x640000. Two binaries tagged MHUI start at 0x144000 and 0x16e000. Their headers have matching coordinate bounds and consistent length fields, but their purpose and filenames remain unverified.

## story000_bvh4.rpf control

This 5,632-byte sample is a compact test case for indexed extraction. The front region ends at 0x340, the candidate front block is 0x310 to 0x340, and the candidate trailer is 0x1570 to 0x1600. The count-like field is 4. The four checksum-verified zlib streams account for every nonzero byte between the front region and the candidate trailer. Each stream decodes to a complete XML document.

| Stored range | Decoded bytes | XML root |
| --- | ---: | --- |
| 0x340 to 0x4f1 | 800 | CDataFileMgr__ContentChangeSetDef |
| 0x1000 to 0x1291 | 14,426 | CDataFileMgr__ContentChangeSetDef |
| 0x12a0 to 0x13bd | 622 | CDataFileMgr__ContentDef |
| 0x13c0 to 0x1564 | 829 | SSetupData |

The observed offsets and lengths, including 16-byte unit variants, did not occur as plain 32-bit or 64-bit integers in either candidate metadata block. The map provides four exact ranges for testing a decoded table. Entry boundaries are still inferred from the streams.

~~~sh
cargo run --locked -- map ../rage-tools-vi/story000_bvh4.rpf
~~~

### Entry field tests

The four-stream control lets us test an entire field across every row. The [fixed-stride probe](tools/probe_index_layout.py) searches the 48-byte front block and the 144-byte trailer for any four-value offset or length field. It tests widths from 6 to 32 bits, arbitrary bit positions, byte-aligned strides, both byte orders, and all four-entry permutations. It covers archive-relative and payload-relative offsets, stored and decoded sizes, lengths rounded to 16 bytes, and occupied slots through the next payload or trailer. The tested field transforms are direct values, one common additive bias, and one common XOR mask.

The probe tested 88,787 fields in the front block and 1,232,400 fields in the trailer. It found no offset field covering all four payloads. Five biased or masked length candidates matched in the trailer, but none paired with an offset field. A synthetic control with four plaintext 12-byte records at 0x310 correctly produced a compatible offset and size pair.

A separate scan for unsigned LEB128 found no complete set of four offsets in either region. Starting at the candidate boundaries, zlib, raw DEFLATE, gzip, bzip2, and xz/LZMA yielded no complete decode of either block. These probes leave other layouts and encodings open.

The setup XML at 0x13c0 points to content.xml. The content definition at 0x12a0 references two changeset paths whose basenames match the internal IDs of the documents at 0x340 and 0x1000. These associations supply independent candidate names. Plain JOAAT and CRC32 variants of the candidate paths did not occur in either block. There is still no indexed range to cross-check against common.rpf.

~~~sh
python3 tools/probe_index_layout.py ../rage-tools-vi/story000_bvh4.rpf
~~~

## Comparisons within the same build

The three workspace archives yielded 2,015 verified zlib stream instances with 1,872 distinct inflated bodies. No decoded body repeated across the archives. Inside script.rpf, three groups of compressed streams were byte-identical, with 120, 18, and 8 instances. The largest group stores 688 bytes per instance and inflates to 1,200 bytes.

The 120 copies give us a frequency test for a plain size field in the large embedded pack. I counted the stored and decoded sizes in bytes and 16-byte units across the candidate front block and trailer. The scan used both bit orders, widths of 8, 12, 16, 20, 24, 28, and 32 bits, and every fixed bit alignment. No candidate representation occurred 120 times at a single alignment. That weighs against a plain size field in any of the tested layouts if those streams correspond to independent entries. The copies could also be indexed or encoded differently.

A text search of the 259 recovered common.rpf XML documents found no explicit companion package catalog or index reference.

## core_licenses_data.rpf control

This 13,536-byte sample has a root front region from 0x0 to 0x330, a 48-byte candidate front block at 0x300, and a 144-byte candidate trailer at 0x3450. The root count-like field is 4.

Four candidate payload envelopes account for every nonzero byte of the parent payload area. Three are complete checksum-verified XML zlib streams. The fourth starts with an embedded RPF9 header. Its candidate end follows the embedded trailer and precedes the zero padding at 0x2e50.

| Stored range | Decoded bytes | Observed content |
| --- | ---: | --- |
| 0x1000 to 0x2e50 | | Embedded RPF9, with opaque spans at 0x1320–0x1520 and 0x2000–0x2e00 |
| 0x3000 to 0x3196 | 763 | CDataFileMgr__ContentChangeSetDef |
| 0x31a0 to 0x32a7 | 455 | CDataFileMgr__ContentDef |
| 0x32b0 to 0x3445 | 786 | SSetupData |

The changeset XML names data/licenses/license_additional_content.rpf as a dependency. That is a candidate name for the embedded archive. Its table and two opaque spans remain undecoded. Searching the root front block and trailer for 32-bit offsets and lengths, in bytes and 16-byte units, found no match for any of the four envelopes.

The first 32 bytes of the root trailer exactly match the trailer in story000_bvh4.rpf. Those archives share the observed count of 4, a 48-byte candidate front block, and a 144-byte trailer. Their payload ranges and remaining trailer bytes differ. The 80-byte trailer of the embedded core_licenses_data pack also shares its first 16 bytes with both count-2 packs previously identified in script.rpf. This suggests a shared metadata prefix, with more than one explanation for what it represents.

~~~sh
cargo run --locked -- map ../rage-tools-vi/core_licenses_data.rpf
cargo run --locked -- map ../rage-tools-vi/core_licenses_data.rpf 1000 2e50
~~~

### Trailer comparison across the controls

The observed shared prefix is 16 bytes across the three count-2 packs and 32 bytes across the two count-4 packs. Both are consistent with eight bytes per count unit. This relationship is currently supported by only two distinct counts. The total trailer size varies within the count-2 group.

Both count-4 trailers have 112 bytes after the shared prefix. Candidate full paths inferred from each sample's XML produce NUL-terminated strings of 109 and 111 bytes when including setup2.xml as the hypothesized setup name. Both fit in 112 bytes after 16-byte alignment. The same candidate basenames or paths with extensions removed would fit in 96 bytes. A search across 2,304 candidate path orders, slash conventions, and setup names did not match the trailer suffixes under a shared XOR mask. Standard zlib, raw DEFLATE, gzip, bzip2, and xz/LZMA did not decode either the full trailer or its suffix. The path lengths offer a hypothesis for the suffix. Its contents and encoding remain unverified.

The fixed-stride probe also ran against the licenses control. It tested 88,978 fields in the front block and 1,231,395 in the trailer. No field matched all four candidate offsets or any tested four-value size set. The embedded archive's decoded size is unknown, so this control tests stored lengths and occupied slots. The story control still tests decoded sizes as well.

~~~sh
python3 tools/probe_index_layout.py ../rage-tools-vi/core_licenses_data.rpf
~~~

## appdata0.rpf control

This 8,880-byte sample has a count-like value of 2, a 32-byte candidate front block at 0x340–0x360, and a 64-byte candidate trailer at 0x2270–0x22b0. Its two candidate payload spans are 0x360–0x550 and 0x1000–0x2270, separated by 2,736 zero bytes. The scan found no complete zlib streams at any alignment. The two spans also yielded no complete match for the tested zlib, raw DEFLATE, gzip, bzip2, or xz/LZMA decoders at their starts or the tested short header skips. Direct 32-bit offsets and lengths in bytes or 16-byte units did not match in the candidate front block or trailer.

The first 16 trailer bytes match all three other count-2 packs. The first 32 bytes match the embedded script.rpf pack at 0x1000, which also has a 64-byte trailer. The remaining 32 bytes differ, as do the payload ranges. The observed eight-bytes-per-count relation describes the common prefix across each small count group. It does not predict every shared byte when trailer sizes also match. A repeatable first block or framing is plausible, and the sample does not identify its decoded contents.

~~~sh
cargo run --locked -- map ../rage-tools-vi/appdata0.rpf
~~~

## Metadata statistics across the samples

The packs command reports Shannon entropy in bits per byte. The front measurement starts at 0x60 and ends at the header's front-region boundary. The front-block measurement starts at the separate boundary in +0x08. The trailer measurement uses the supplied pack end and the byte length in +0x0c. An embedded header found during a scan has no trailer measurement until its pack bounds are supplied.

| Pack | +0x24 | Front | Front block | Trailer |
| --- | ---: | ---: | ---: | ---: |
| appdata0.rpf | 2 | 7.7263 | 4.9375 | 5.6757 |
| common.rpf | 418 | 7.9950 | 7.9572 | 7.9889 |
| core_licenses_data.rpf | 4 | 7.7174 | 5.3766 | 6.5604 |
| core_licenses_data.rpf at 0x1000 | 2 | 7.6919 | 4.8750 | 6.0281 |
| script.rpf root | 2 | 7.5690 | 4.8750 | 6.5976 |
| script.rpf at 0x1000 | 2 | 7.8125 | 4.8750 | 5.7188 |
| script.rpf at 0xc4000 | 1,012 | 7.9976 | 7.9850 | 7.9934 |
| story000_bvh4.rpf | 4 | 7.7237 | 5.2933 | 6.6681 |

The 38,176-byte common.rpf front span has a one-bit fraction of 0.50052 and a byte-frequency chi-squared statistic of 266.42 on 255 degrees of freedom. Shorter spans have lower maximum measured entropy. A 64-byte span can reach at most 6 bits per byte on this statistic. Across 9,801 aligned 16-byte blocks from the observed fronts and trailers, the only repeats were the four shared trailer-block groups described above. All eight observed headers share the 32 bytes at +0x40.

These results describe the stored bytes. They leave the encoding, cipher, and location of any key material unresolved. The plain offset probes and attempted standard compression decodes are narrower tests. The original indexed-extraction milestone still requires a decoded record that independently predicts a verified payload range.

The four XML outputs in [output/story000_bvh4](output/story000_bvh4) in the original checkout were independently matched to their zlib streams byte-for-byte. Their IDs and paths are useful dictionary candidates. The changeset documents reference dependencies, and the name attached to each payload by RPF9 is still unverified.

## Comparing candidate partitions with the header count

The partition command reports checksum-verified zlib streams, candidate zlib chains, opaque spans, and inferred embedded packs separately. Physical coverage is reported as a byte budget. Zlib bytes, opaque bytes, inferred embedded-pack bytes, and zero runs sum to the payload span. A zero run identifies bytes with value zero. An opaque span and a candidate chain may each correspond to one file, several files, or a fragment.

| Pack | +0x24 | Verified streams at this level | Candidate chains | Opaque spans | Inferred embedded packs | Candidate total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| common.rpf | 418 | 954 | 277 | 117 | 0 | 394 |
| script.rpf root | 2 | 0 | 0 | 0 | 2 | 2 |
| script.rpf at 0x1000 | 2 | 42 | 1 | 1 | 0 | 2 |
| script.rpf at 0xc4000 | 1,012 | 1,015 | 1,012 | 0 | 0 | 1,012 |
| story000_bvh4.rpf | 4 | 4 | 4 | 0 | 0 | 4 |
| core_licenses_data.rpf | 4 | 3 | 3 | 0 | 1 | 4 |
| core_licenses_data.rpf at 0x1000 | 2 | 0 | 0 | 2 | 0 | 2 |
| appdata0.rpf | 2 | 0 | 0 | 2 | 0 | 2 |

The candidate totals match the header field in seven of eight observed scopes. For nested archives, the child count-like field helps select a candidate end, so the agreement is partly conditional on the heuristic. The independent payload audit below verifies the 42-stream object, the PSIN record layouts, and complete XML documents. Complete file-by-file extraction remains unverified.

The nested resolver tests 16-byte-aligned ends at the next header, the parent payload end, or the start of a zero run of at least 256 bytes. A candidate must leave nonzero bytes in the final block of the proposed trailer and produce the child header's candidate count. The report lists an unresolved header when zero or multiple ends pass. The corrected resolver reports 0x1000–0xc3b90 and 0xc4000–0x4282b0 for the script.rpf children, and 0x1000–0x2e50 for the core_licenses_data.rpf child. Bytes between those extents remain visible in the parent scan.

The command retains all 117 opaque spans of common.rpf, including short spans. The resulting candidate total is 394, which is 24 below 418. Of the 30 chains made of exactly two zlib streams, 27 reconstruct complete XML, so splitting those chains would break valid documents. The physical byte balance accounts for every byte even when the candidate grouping is uncertain.

Seven changeset references match internal IDs in XML recovered from common.rpf. The level manifest also references `common:/data/levels/americas/heightmap.dat`, a candidate association for the decoded HMAP. Stripping the mount prefixes from these eight candidate paths leaves four directory prefixes: `changesets`, `data`, `data/levels`, and `data/levels/americas`. The audit's six prefix nodes include the two mount labels. This partial path sample leaves the 24-record gap unresolved. Opaque spans can contain multiple payloads or continue nearby chains, and the header count may include records without payloads.

## File signature scan of the opaque spans

Libmagic reported both appdata0.rpf spans, both embedded core_licenses_data.rpf spans, and the opaque span in the small embedded script.rpf pack as generic data. In common.rpf, 105 of 117 unclassified spans were generic data. Six matched AIN and four matched DOS COM. Libmagic reproduced those labels with as little as two and four input bytes respectively. These are signature matches without structural confirmation.

Two unclassified common.rpf ranges start with the zlib header `78 da`. Raw DEFLATE decoding after that header gives two distinct failures. Stored ranges are start-inclusive and end-exclusive.

| Stored range | Raw DEFLATE result | Adler-32 |
| --- | --- | --- |
| `0x212190..0x212f20` | 5,239 bytes from the first dynamic block. The next block exceeds its code-length table at input byte `0x212437`, before a stream terminator. | Unavailable |
| `0x21ba50..0x21d0dd` | 71,243 bytes from one final dynamic block, ending at `0x21c5f7`. The wrapped probe had emitted 71,072 bytes before reporting the checksum failure. | Apparent trailer `7ae22a8e`, calculated `e8db2239`. Another 2,786 stored bytes follow the apparent trailer. |

Both prefixes match the XML context of earlier verified chunks. The first finishes an attribute value started in the second 64 KiB chunk of the chain at `0x210a70`. The second continues the tag list in the 64 KiB chunk at `0x21ad30`, with malformed tag text observed at its own decoded offset `0xf002`. These joins support treating both spans as candidate continuations. Their decoded bytes remain unverified and the range mapper still reports both stored spans as unclassified.

## Archive-only payload partition audit

The [payload audit](tools/audit_payload_objects.py) checks the range map with an independent zlib decoder, then validates reconstructed objects separately. The count-like field remains a cross-check. It is not used to assign boundaries.

| Pack | Verified streams | Structurally verified decoded objects | Unclassified spans |
| --- | ---: | --- | ---: |
| script.rpf at 0x1000 | 42 | 1 offset-linked binary object | 1 |
| script.rpf at 0xc4000 | 1,015 | 1,012 PSIN records, including 3 continuations | 0 |
| story000_bvh4.rpf | 4 | 4 complete XML documents | 0 |
| common.rpf | 954 | 259 complete XML documents out of 277 candidate zlib chains | 117 |

The script.rpf stream count reconciles exactly as 42 + 1,012 + 3 = 1,057, with no verified zlib streams outside the two embedded pack envelopes. Those envelopes account for every nonzero byte of the parent payload region.

The compact script.rpf pack has 41 decoded chunks of 65,536 bytes and a final chunk of 15,408 bytes. The reconstructed binary is 2,702,384 bytes. Its little-endian count at decoded offset 0x14 is 30,683. An array of 64-bit offsets starts at 0x28 and ends at 0x3bf00, which is also the first listed object offset. All 30,683 offsets are strictly increasing, 16-byte aligned, and in bounds. The last is 0x293c00, 48 bytes before the reconstructed end and inside the final chunk. All 30,200 aligned references with upper word 0x71717171 point exactly eight bytes past a listed offset. Of those references, 1,324 cross decoded-chunk boundaries. This structure supports treating the 42 streams as a single object. The other candidate payload is an opaque span, and its entry boundaries and codec remain unverified.

Counting each common.rpf candidate zlib chain and each unclassified span once would give 394 groups. The header's count-like field is 418. Unclassified spans can contain several entries or parts of adjacent entries, and the meaning of the count remains open. An aligned zlib scan widened to all permitted window-size codes found the same 954 complete streams without preset dictionaries. Candidate headers with a preset-dictionary flag remain unvalidated.

~~~sh
cargo build --locked
python3 tools/audit_payload_objects.py ../rage-tools-vi
~~~

### Extracting the small script.rpf control

The range extraction commands take an inclusive start and exclusive end. The zlib mode validates every checksum, requires full 64 KiB decoded chunks before each continuation, and checks intervening zero padding. The command buffers the reconstructed chain and writes it after validation. The raw mode copies the supplied bytes directly. Both commands refuse an existing output path.

From the repository root, the following commands extract one decoded binary and its neighboring opaque range. The structured-object audit independently checks the binary's internal offsets.

~~~sh
mkdir -p output/script.rpf
cargo run --locked -- extract-zlib script.rpf 53000 c3b45 output/script.rpf/053000-0c3b45.bin
cargo run --locked -- extract-raw script.rpf 2010 52fe0 output/script.rpf/002010-052fe0.raw
~~~

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| 053000-0c3b45.bin | 2,702,384 | 592afd44c211a8d07ca7f90ef3f8659d272b2d271b5a9a85ed735a5ed80c3c82 |
| 002010-052fe0.raw | 331,728 | b5d622ca79058af2578b753002899ebc8b89b09d09edf1fc8071bc84bb4dc28e |

The new mode also reproduced all four single-stream XML files from story000_bvh4.rpf and all three two-stream PSIN records from script.rpf. A truncated final stream and an end set beyond the final checksum were rejected before opening the output file.

### Inspecting the extracted binaries

The 2,702,384-byte decoded object has byte Shannon entropy of 3.1704. Libmagic reports generic data, and scans found no recognizable wrapper, path-shaped text, or complete nested zlib stream. Its internal layout provides stronger evidence than the byte signatures.

All 30,200 tagged references point forward and have distinct targets. The records therefore form a forest of 483 roots and 10,833 leaves. Every subtree occupies a contiguous interval in record order. Each root starts with a distinct nonzero 32-bit value, and every other record starts with zero. The meanings of these values remain unknown. There are 81 observed record span sizes, ranging from 32 to 6,704 bytes. The first root at decoded offset 0x3bf00 covers 207 records and ends at 0x45390.

Of the 483 roots, 482 occupy 32-byte records and one occupies 48 bytes. Tagged references fall at multiples of eight bytes within records, most often at offsets `+0x10` (12,335 references) and `+0x18` (5,184).

All 1,012 PSIN records have an eight-byte `LGID` section consisting entirely of its header. A scan of 3,474,836 four-byte windows in both byte orders for the 483 root IDs found two matches in `LSNS` and one in `PSIN`. They occur at different section offsets and use mixed byte orders. The result leaves the relationship between the root IDs and PSIN records unresolved.

The 331,728-byte raw range has byte Shannon entropy of 7.9961. Libmagic reports generic data and the scan found no recognizable wrapper, path-shaped text, or complete nested zlib stream at any byte alignment. The apparent 112-byte repeat comes from a seven-byte sequence, `7e9e81e0e71908`, repeated 54 times over 378 bytes at raw offsets `0x14470..0x145ea` (archive offsets `0x16480..0x165fa`). A search for the seven aligned 16-byte blocks of the original 112-byte window across 126 unclassified spans in four archives found matches only inside this run. Its encoding and contents remain unknown.

## Metadata region scaling (review)

Each header splits into three candidate regions: Front A from `+0x60` to the
front-block boundary at `+0x08`, Front B from `+0x08` to the front-region end at
`+0x04`, and the trailer from `end - +0x0c` to `end`. The table uses the eight
observed scopes and the candidate counts from the partition report.

| Scope | N (+0x24) | Streams | Chains | Opaque | Embedded | Candidates | Front A | Front B | Trailer | A/cand | B/N | T/N |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| appdata0 | 2 | 0 | 0 | 2 | 0 | 2 | 736 | 32 | 64 | 368.00 | 16.00 | 32.00 |
| common | 418 | 954 | 277 | 117 | 0 | 394 | 33,984 | 4,192 | 14,864 | 86.25 | 10.03 | 35.56 |
| core root | 4 | 3 | 3 | 0 | 1 | 4 | 672 | 48 | 144 | 168.00 | 12.00 | 36.00 |
| core at 0x1000 | 2 | 0 | 0 | 2 | 0 | 2 | 672 | 32 | 80 | 336.00 | 16.00 | 40.00 |
| script root | 2 | 0 | 0 | 0 | 2 | 2 | 480 | 32 | 128 | 240.00 | 16.00 | 64.00 |
| script at 0x1000 | 2 | 42 | 1 | 1 | 0 | 2 | 1,024 | 32 | 64 | 512.00 | 16.00 | 32.00 |
| script at 0xc4000 | 1,012 | 1,015 | 1,012 | 0 | 0 | 1,012 | 61,232 | 12,160 | 25,264 | 60.51 | 12.02 | 24.96 |
| story000_bvh4 | 4 | 4 | 4 | 0 | 0 | 4 | 688 | 48 | 144 | 172.00 | 12.00 | 36.00 |

Every Front A, Front B, and trailer length is a multiple of 16. The small
tables are two or three AES blocks. This is consistent with block padding, but
does not by itself prove a cipher.

**Front B is content-independent at fixed N.** All four N = 2 scopes have a
32-byte Front B whether they hold two embedded packs, two opaque spans, or a
42-stream object. Both N = 4 scopes have 48 bytes. The two large scopes break a
single fixed-width record model: 4,192 bytes is 10.03 bytes per count unit at N
= 418, and 12,160 bytes is 12.02 at N = 1,012, after 16.0 at N = 2 and 12.0 at N
= 4. A lookup table would need a changing capacity or record width, or the table
would need compression before padding.

**Trailer prefixes form two groups, not one.** The four N = 2 scopes share the
same first 16 bytes, but they split at 32 bytes: appdata0 and script at 0x1000
share a 32-byte prefix and diverge at byte 32, while core at 0x1000 (80-byte
trailer) and script root (128-byte trailer) retain only the 16-byte prefix. The
two N = 4 scopes share a different 32-byte prefix and also diverge at byte 32.
common and script at 0xc4000 have unique 32-byte prefixes. The review's
statement that the first 32 bytes match across root and embedded scopes is true
within each pair, not across all eight scopes. The shared prefix cannot hold
payload offsets for packs with different payload spans; the divergent suffix is
not excluded. The N = 4 suffix is 112 bytes after the shared prefix, enough for
the 109- and 111-byte candidate path strings.

| Scope | Front A | Rest after 0x60..0x160 | H(0x60..0x160) | H(rest) |
| --- | ---: | ---: | ---: | ---: |
| appdata0 | 736 | 480 | 7.2493 | 7.5372 |
| common | 33,984 | 33,728 | 7.0935 | 7.9938 |
| core root | 672 | 416 | 7.1863 | 7.5042 |
| core at 0x1000 | 672 | 416 | 7.1585 | 7.4525 |
| script root | 480 | 224 | 7.1746 | 7.1385 |
| script at 0x1000 | 1,024 | 768 | 7.1463 | 7.7261 |
| script at 0xc4000 | 61,232 | 60,976 | 7.1594 | 7.9972 |
| story000_bvh4 | 688 | 432 | 7.0887 | 7.4913 |

Both halves of Front A are high-entropy. The 256-byte split at `+0x160` matches
an RSA-2048 signature size and leaves 224 to 60,976 bytes, but the entropy does
not show a boundary. The leftover does not scale monotonically with stream
count: script root has 224 bytes and no verified streams, core at 0x1000 has 416
and no verified streams, and appdata0 has 480 and no verified streams. The review's
"scales with chunk/stream count" hypothesis is therefore not established.

Header words across the eight scopes:

| Offset | Values |
| --- | --- |
| `+0x10`, `+0x14` | An 8-byte per-scope value; all eight pairs are distinct. |
| `+0x18` | `0x00047a00` in every scope. |
| `+0x1c` | `0x00000150` in every scope. |
| `+0x20` | `0x00010003`, `0x00010005`, `0x00010006`, `0x00010007`, or `0x00020006`. |
| `+0x28` | `0xda72573e` in five scopes; core root, script root, and script at 0x1000 differ. |
| `+0x2c` | `0x00090f01` for the small scopes; `0x00090f02` for common and script at 0xc4000. |
| `+0x30` through `+0x3c` | `0x00000010`, then three zero words. |
| `+0x40` through `+0x5c` | The same eight words in all eight scopes. |

The constant `+0x40..+0x60` block remains the best build-wide key or KDF-fingerprint
candidate. The per-scope `+0x10..+0x14` value and `+0x28` cannot derive a trailer
prefix that is shared across packs. The constant `+0x40..+0x60` block can, if it
is combined with a per-pack input such as N or the trailer length.

The per-candidate budget is 60.5 bytes in script at 0xc4000 and 86.25 bytes in
common. The trailer budget is 25.0 and 35.6 bytes. Front A has the most room for
offset, size, and hash fields, but the trailer suffix is not ruled out by size.
Front A is also high-entropy, so a plaintext field probe would sample random
bytes until the cipher is characterized. The fixed-stride probe has so far run
only against Front B and the trailer.

The directory hypothesis does not yet close the common.rpf gap. The recovered
XML references 76 `common:` paths and 28 `$(root)` paths, which produce 16 and 2
non-mount directory prefixes respectively: 18 directories, or 20 prefix nodes
including the two mount labels. Starting from 394 candidate groups, 394 + 18 =
412 and 394 + 20 = 414, not 418. The reference set is not the archive's own
directory table, and candidate groups can merge or split, so the 24-entry gap
alone cannot confirm the directory explanation. Decoding one directory node
would.

~~~sh
cargo build --locked
python3 tools/metadata_regions.py .
~~~

## Trailer mode and header derivation (review item 2, first pass)

The first trailer test XORs the divergent suffixes of the two pairs that share a
32-byte prefix. [tools/metadata_regions.py](tools/metadata_regions.py) reports:

| Pair | Suffix bytes | Bit-7 ones | Value range |
| --- | ---: | ---: | --- |
| appdata0 vs script at 0x1000 | 32 | 21 (65.6%) | 22..253 |
| core root vs story000_bvh4 | 112 | 58 (51.8%) | 0..250 |

A shared-keystream stream cipher over ASCII path names would leave bit 7 clear
at almost every position, because ASCII is `0x00..0x7f`. Both diffs are close to
random. This disfavors a shared-keystream CTR or ChaCha model for the trailer
suffix. It does not distinguish AES-CBC from CTR with a per-pack nonce or offset,
and it does not decode a name.

The same tool's header words narrow the shared derivation candidates. These are
the fields that differ inside each pair:

| Pair | Differing fields |
| --- | --- |
| appdata0 vs script at 0x1000 | `+0x04`, `+0x08`, `+0x10`, `+0x14`, `+0x20` low half, `+0x28` |
| core root vs story000_bvh4 | `+0x04`, `+0x08`, `+0x10`, `+0x14`, `+0x28` |

Within each pair, `+0x18`, `+0x1c`, `+0x24`, `+0x2c`, `+0x30..+0x3c`, and
`+0x40..+0x60` are identical. The pairs still have different trailer prefixes:
N (`+0x24`) is 2 in the first pair and 4 in the second, and the trailer length
(`+0x0c`) is `0x40` and `0x90`. A shared seed must therefore be combined with a
per-pack input such as N or the trailer length. The constant `+0x40..+0x60` block remains the best
build-wide key or KDF-seed candidate; `+0x18`, `+0x1c`, and `+0x2c` are also
constant and could be format or version words instead of key material. A second
build is needed to separate those roles.

## Script section block structure (review item 2)

The 1,012 PSIN records at `0xc4000` contain seven sections. The table strips the
eight-byte tag and size header first; `header` is the additional plaintext prefix
removed before comparing aligned 16-byte blocks. First-block predecessors use the
IV sentinel. `diff_pred` counts occurrences of a repeated block whose preceding
block differs from the other occurrences of that value.

| Section | Header | Body length | Blocks | Unique | Repeated values | Repeated occurrences | Same pred | Diff pred |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PSIN | 8 | 216..110,536 | 106,831 | 33,484 | 7,220 | 80,567 | 67,695 | 12,872 |
| LSCH | 16 | 464..544 | 32,611 | 32 | 32 | 32,611 | 32,611 | 0 |
| LENM | 8 | 120 | 7,084 | 7 | 7 | 7,084 | 7,084 | 0 |
| LSNS | 12 | 44..19,404 | 58,697 | 52,632 | 1,301 | 7,366 | 7,366 | 0 |
| LGID | none | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| LRSC | 16 | 80 | 4,048 | 7 | 7 | 4,048 | 4,048 | 0 |
| CHKS | none | 12 | 0 | 0 | 0 | 0 | 0 | 0 |

**Only LSNS is chained-encrypted.** It has 52,632 unique blocks. All 7,366
repeated occurrences have the same predecessor, and 853 first blocks repeat. The
12-byte plaintext header is `(1, 257, block_bytes)` in all 1,012 records, and
`block_bytes` equals the payload length and is a multiple of 16. That is the CBC
signature with a fixed or deterministic chaining value and a build-wide key; a
per-record random IV would not produce 853 first-block repeats, and ECB would
produce repeats with different predecessors. The blocks are high-entropy and
contain no visible padding, so LSNS is not plaintext.

**PSIN is plaintext.** It has 7,220 repeated values, but 12,872 occurrences have
a different predecessor. Frequent blocks contain visible 8-byte IDs, zero fields,
small tags, and `0xaa` padding; for example `7268d2676b5c3c6e0000000003010000`
occurs 4,473 times. This is a hash or index table, not ciphertext.

**LSCH is a fixed plaintext template.** It has only 32 unique blocks across
32,611 aligned blocks, with `0xaa` padding, zero fields, small counts, and
repeated hashes. Its 464- and 544-byte bodies are not encrypted.

**LENM and LRSC are fixed plaintext tables.** LENM is 120 bytes: an eight-byte
header, a marker block `eeeeeeeeeeeeeeee0600000000000000`, then six 16-byte entries
with a 64-bit index and a 32-bit hash. LRSC is 80 bytes: a 16-byte `0DRP` header,
then 64 bytes of `0xbb` fill, counts 3 and 4, and small fields. LGID is header-only.
CHKS is 12 plaintext bytes holding the total length and checksum.

**Trailer block alignment.** Every shared trailer prefix ends at 16 or 32 bytes,
all multiples of 16. Across all eight trailers, the only repeated aligned blocks
are the shared prefix blocks themselves: four values in ten occurrences. The
first differing byte is always a block boundary. This is consistent with CBC and
inconsistent with a byte-oriented stream cipher that would diverge mid-block. It
does not prove AES, but with the failed XOR crib it makes CBC the leading trailer
hypothesis; the shared 16-byte block is a candidate IV or chaining value.

~~~sh
cargo build --locked
python3 tools/section_blocks.py
python3 tools/metadata_regions.py .
~~~

## Anomalous streams and the script.rpf pair (review item 3)

### common.rpf partial streams

| Item | First span | Second span |
| --- | --- | --- |
| Preceding full chunks | `0x210a70..0x211612`, then `0x211620..0x212182` | `0x21ad30..0x21ba48` |
| Continuation gap | 14 zero bytes, then 14 zero bytes | 8 zero bytes |
| Partial span | `0x212190..0x212f20` | `0x21ba50..0x21d0dd` |
| Raw DEFLATE result | first block ends `0x2123e5` after 5,239 bytes; second block fails at `0x212437` | one final block ends `0x21c5f7` after 71,243 bytes |
| Alignment | failure mod 16 = 7, mod `0x1000` = `0x437`; block end mod 16 = 5 | raw end mod 16 = 7; apparent trailer ends mod 16 = 11 |
| Other | no zlib header elsewhere in the span | stored Adler `7ae22a8e`, calculated `e8db2239`; 2,786 bytes follow the apparent trailer; no zlib header elsewhere in the span |

The continuation rule is now explicit: each 64 KiB chunk is a separate zlib
stream at the next 16-byte-aligned offset, and the gap is zero padding (14 bytes
when the stored end is 2 mod 16, 8 bytes when it is 8 mod 16). Both partial spans
start exactly where the next continuation stream would start. The first decoded
prefix completes the previous chunk's tag (`16.` + `0"/>`), so it is a third
chunk attempt.

The first anomaly is a truncated or damaged third chunk: the first raw block is
valid and emits 5,239 bytes, then the second block fails with an invalid bit
length repeat. The failure is neither 16-byte nor 4 KiB aligned. The bytes at the
block boundary `0x2123e5` are compressed data, not a framing header, and no other
zlib stream starts inside the span. The rest of the span cannot be decoded.

The second anomaly is not a normal 64 KiB chunk. It decodes 71,243 bytes in one
final DEFLATE block, crossing the 64 KiB boundary with no new stream, and its
apparent Adler-32 does not match. The decoded text is malformed from `0xf002`
until `<tags>` resumes at `0xf239`. `0xf002` is two bytes after the `0xf000` 4
KiB boundary, and `0xf002 + 14 = 0xf010` is 16 bytes after it, but there is no
14-byte header at that point and the text stays malformed for 567 bytes. The
2,786 trailing bytes contain no valid zlib header. This span may contain more
than one object, or it may be damaged; the index is needed to decide. Neither
anomaly is explained by a page-sized or 16-byte framing header inserted after a
full chunk.

### script.rpf at 0x1000

| Property | 42-stream object | Opaque blob |
| --- | --- | --- |
| Stored range | `0x53000..0xc3b45` | `0x2010..0x52fe0` |
| Decoded bytes | 2,702,384 | 331,728 |
| Entropy | 3.1704 | 7.9961 |
| Structure | 30,683 records, 483 roots, 30,200 tagged references | 16-byte multiple, no complete zlib stream at any byte alignment |
| Tree index in blob | 0/30,683 offsets and 0/30,200 targets as 8-byte LE; one low-32 offset and one low-32 target match | 0/483 root IDs little-endian, one big-endian |

The object is a self-referential relocation table: every tagged reference points
to an address eight bytes past a record offset in the same object. It does not
store blob offsets. The blob size `331,728` does not occur in the object or the
blob, and the root records contain IDs and record targets rather than a blob size
table. The pair is structurally the pack's two entries, but a direct index from
the 483 roots into the blob is not established; the low-32 matches are at the
random expectation.

The blob contains two short periodic island runs: 54 repeats of the seven-byte
unit `7e9e81e0e71908` at `0x14470..0x145ea` (378 bytes), and 16 repeats of a
different seven-byte unit at `0x145ed..0x1465d` (112 bytes). XORing the first run
with its own unit necessarily yields zeros, so that result alone does not prove a
key. The second, adjacent run uses a different unit, which argues against a
single seven-byte XOR key over zero-filled regions and more for repeated
plaintext or bytecode patterns. Using the first unit as a candidate repeating key
over the whole blob produces no zlib stream and no printable run longer than 14
bytes, so the rest of the blob is not decoded by it. The blob is therefore not
uniformly AES-CBC ciphertext because secure block modes would not preserve a
seven-byte period; whether the runs are keyed zeros or repeated plaintext remains
open. The blob may be bytecode with repeated patterns or a partially obfuscated
container.

~~~sh
cargo build --locked
python3 tools/script_pair.py
python3 tools/pi_archive_audit.py .
~~~

## Object-tree root names (new)

The 483 root records start with distinct 32-bit IDs. [tools/root_names.py](tools/root_names.py)
matches **306 of 483** against JOAAT hashes of identifiers in the recovered XML,
a system word list, and one vehicle-feature probe. Examples:

| Name | JOAAT |
| --- | --- |
| `duster` | `0x39d6779e` |
| `shamal` | `0xb79c1bf5` |
| `shifter` | `0xae679517` |
| `airbus` | `0x4c80eb0e` |
| `banshee` | `0xc1e908d2` |
| `ambulance` | `0x45d56ada` |
| `car_hydraulics` | `0xa3d20e87` |

The match count is not accidental: 483 roots against 328,823 candidate strings
gives a random expectation of about 0.04 matches. The first word of a root record
is therefore a JOAAT name hash. The named roots are mostly vehicle model names;
`car_hydraulics` shows that the set also contains vehicle features or subsystems.
The remaining 177 roots are not in the current dictionary. A cross-check against
DurtyFree's GTA V [VehicleList](https://github.com/DurtyFree/gta-v-data-dumps/blob/master/VehicleList.ini),
WeaponList, PedList, and ObjectList adds 11 vehicle roots beyond the XML, such as
`baller7`, `everon`, and `italigto`, and no weapon, ped, or object roots. The
remaining roots are not in those public lists; they may be vehicle features or
script-local objects. The record fields and the 30,200 tagged references are
still undecoded, but the named roots provide anchors for walking the subtrees and
for testing whether the blob stores their data or offsets.

### Object-tree name fields

A scan of all four-byte words in the object against the same name dictionary finds
**703 name hits**, about 59 expected by chance, and 331 unique names. The field
positions cluster at `+0x10` (359 hits), `+0x0` (306), and `+0x30` (12). The
frequent names are vehicle parts and bones: `boot` (177), `bonnet` (111),
`chassis` (10), `handlebars` (7), `skel_spine1`, `skel_l_calf`, and others.

The hierarchy is visible directly. For example, `airbus` has a `boot` child,
`aleutian` has `bonnet` and `boot`, and `216cstreamer` has `dodo`. The roots are
vehicle model names and the child fields are part, bone, or component names.
This makes the 2.7MB object a named vehicle model and part hierarchy, not only a
relocation table. Sampled part records contain name hashes, tagged tree offsets,
small counts, and float transforms such as `-0.1` and `0.1`.

No sampled part field falls in the blob's `0..331,728` range, and a JOAAT scan of
the blob finds 12 hits against about 7 expected. The blob therefore has no
detected name-table or part-offset structure. It is likely a separate bytecode
or data resource, not an index into the named tree. The object as a whole is
consistent with a serialized parCodegen/pgBase object graph: fixed C++ structs
linked by `0x71717171` tagged relative pointers.

### Struct groups

Grouping each record by `(record_size, tagged-pointer offsets)` partitions the
30,683 records into **136 struct layouts over 81 sizes**. The largest groups:

| Records | Size | Pointer offsets | Role |
| ---: | ---: | --- | --- |
| 12,332 | 32 | `+0x10` | anonymous pointer record; almost no name hits |
| 3,540 | 32 | `+0x18` | named root or part record; contains all named roots and parts |
| 3,521 | 64 | none | data block |
| 2,070 | 144 | none | data block |
| 1,641 | 48 | `+0x18`, `+0x20` | two-pointer record |
| 1,231 | 32 | none | anonymous 32-byte data |
| 912 | 64 | `+0x48` | pointer at the end |
| 660 | 64 | `+0x48`, `+0x56` | two trailing pointers |

All named roots and parts fall in the 32-byte, `+0x18`-pointer group. Its layout
is consistent with `[u32 name][u32 flags][u32 hash][u32 zero][u32 value or float]`
followed by a tagged pointer at `+0x18`. A root such as `aleutian` at `0x1a6fc0`
has name `0xfdaebf27`, flags `0xffff0000`, hash `0xc48ab516`, a float-like
`0x4266e537` (57.7), and the tagged pointer. A part such as `boot` at `0x1a5130`
has zero at `+0x0`, a hash at `+0x8`, the name `0xb55e9119` at `+0x10`, and the
pointer at `+0x18`. LSCH's `name`, `attributes`, `flags`, `heading`, and `root` are
candidate field names for this layout; the transform blocks remain to be matched.

### Schema field names

[tools/schema_names.py](tools/schema_names.py) scans the plaintext LSCH and PSIN
bodies for JOAAT matches. The recurring names are coherent schema fields:

| Section | Field | JOAAT | Recurrence |
| --- | --- | --- | ---: |
| LSCH | `attributes` | `0x749dbb9e` | 1,012 |
| LSCH | `name` | `0xe6e17f14` | 1,012 |
| LSCH | `x` | `0x9303a5e5` | 855 |
| LSCH | `y` | `0x80950108` | 855 |
| LSCH | `z` | `0xb6606c9e` | 855 |
| PSIN | `datatype` | `0x9b21d37f` | 198+ |
| PSIN | `name` | `0xe6e17f14` | 198+ |
| PSIN | `flags` | `0x67d26872` | 178+ |
| PSIN | `item` | `0xd3b360c4` | 149+ |

The `x`, `y`, `z` triplet appears at LSCH offsets `0x160`, `0x170`, and `0x180`
in 855 records, consistent with a position or vector descriptor. PSIN contains
serialized instances with named fields (`datatype`, `name`, `flags`, `item`).
LSCH and PSIN therefore form the plaintext schema and instance layer for the
object graph, not just opaque payload bytes.

~~~sh
cargo build --locked
python3 tools/root_names.py
python3 tools/object_names.py
python3 tools/struct_types.py
python3 tools/schema_names.py
~~~

## Reproduction

The Rust CLI is in [src/main.rs](src/main.rs), with the range mapper in [src/range_map.rs](src/range_map.rs). The map command produces TSV and accounts for every byte in the supplied range. Front and trailer boundaries use the observed header values. Zero runs and unclassified ranges are observations about the bytes.

~~~sh
cargo build --locked
cargo run --locked -- inspect common.rpf
cargo run --locked -- inspect script.rpf
cargo run --locked -- packs common.rpf
cargo run --locked -- packs script.rpf
cargo run --locked -- packs story000_bvh4.rpf
cargo run --locked -- packs script.rpf 1000 c3b90
cargo run --locked -- partition script.rpf
cargo run --locked -- partition script.rpf 1000 c3b90
cargo run --locked -- partition core_licenses_data.rpf
cargo run --locked -- map common.rpf
cargo run --locked -- map script.rpf 1000 c3b90
cargo run --locked -- list script.rpf
cargo run --locked -- sections script.rpf 0xe7000
cargo run --locked -- extract script.rpf 0xe7000 record.psin
~~~

Run `python3 tools/pi_archive_audit.py .` from the repository root after building the CLI to reproduce the raw DEFLATE, root ID, and motif probes. The path association probe also uses the XML extracted to `output/common.rpf/`. See the [Pi payload audit](pi-payload-audit.md) for the individual matches and path associations.

## Journal: documentation split (2026-11-20)

Moved the roadmap, todo, and current state to [plan.md](plan.md). From this point
on, `investigation.md` is append-only: new evidence goes at the end, and status
changes go in `plan.md`.

## Journal: schema and struct partition (2026-11-20)

- `tools/schema_names.py` found the LSCH field names `x`, `y`, and `z` at body
  offsets `0x160`, `0x170`, and `0x180` in 855 records, alongside `name` and
  `attributes`. PSIN adds `datatype`, `name`, `flags`, and `item`.
- Grouping all records by `(size, tagged-pointer offsets)` yields 136 struct
  layouts over 81 sizes. Every named root and part falls in the 32-byte
  `+0x18`-pointer group.
- Root naming now stands at 306 of 483. Public GTA V vehicle, weapon, ped, and
  object lists add only 11 roots beyond the recovered XML.
- Added `tools/schema_names.py` and `tools/struct_types.py`; extended
  `tools/root_names.py` with external name lists and `tools/script_pair.py` with
  a blob JOAAT scan.

## Journal: transform leaves (2026-11-20)

`tools/transform_values.py` follows the `0x71717171` tagged pointers from named
parts to 32-byte leaf records. A rotation leaf has a type hash at `+0x08`
(`0xfc86dde2`) and a float at `+0x10`. The values are radians:

| Part | Frequent float values | Interpretation |
| --- | --- | --- |
| `boot` | -1.25664, -1.57080, -1.30900, -1.13446, -1.57100 | -72, -90, -75, -65, -90 degrees |
| `bonnet` | 1.04720, 1.30900, 1.04700, -1.25664, -0.87266 | 60, 75, 60, -72, -50 degrees |

The exact angle multiples confirm that these leaves are rotation transforms, not
hashes or offsets. `chassis` and the vehicle roots traverse multi-level pointer
nodes; those traversals also reach non-transform leaves, so the tool filters by
the rotation hash. The next transform step is to locate the 3x4 or 4x4 matrix
blocks in the no-pointer records and tie them to the LSCH field offsets.

## Journal: array containers (2026-11-20)

The large no-pointer records are variable-length containers, not matrix blocks.
They have a 48-byte header followed by 16-byte entries:

| Record size | Entries |
| ---: | ---: |
| 64 | 1 |
| 80 | 2 |
| 96 | 3 |
| 112 | 4 |
| 144 | 6 |
| 176 | 8 |
| 192 | 9 |
| 240 | 12 |
| 288 | 15 |
| 336 | 18 |
| 432 | 24 |

The header fields are consistent with `[0][0x14][count][count][0x10][0][0][typeHash]`.
For example, the 176-byte record 8034 at `0x15a5c0` has eight 16-byte entries,
each holding two floats: `(9.736, 3.903)`, `(8.934, 3.908)`, `(8.543, 3.835)`,
and so on. The header type hash is `0xc92cdeca` for that array.

No orthonormal 3x4 or 4x4 matrix block was found in the no-pointer records. The
earlier matrix candidates at offsets 48 and 80 were zero-pattern false positives.
The actual transform data is either in the 16-byte array entries or encoded in a
form not yet identified. `tools/array_records.py` detects the header plus entry
layout.

## Journal: property and array graph (2026-11-20)

Poking at the named `airbus` subtree shows the object graph's container pattern:

- `airbus` root (32 bytes) -> a 32-byte node -> a 112-byte container of seven
  tagged pointers at `+0x30..+0x60`.
- Each 48-byte property node has two pointers: `+0x18` to a key/name node and
  `+0x20` to a value node.
- The key/name node is 32 bytes and points at `+0x10` to an array.
- Arrays have a 48-byte header and data at `+0x30`. The header is consistent with
  `[0][0x14][hash or 0][0][count][count][entry_size][flags]`. `entry_size` is 8
  for pointer arrays and 16 for value arrays.
- The `airbus` property node 12775 points to key 12776, which points to an
  80-byte pointer array of four children. Its value node 12794 is a 64-byte
  record with hash `0x1d8ec2c3` and `1.0, 1.0` at `+0x20`.

The property/key hashes at `+0x08` are not in the current JOAAT dictionary. They
are likely another ID space or a different hash. `tools/property_tree.py` dumps
named subtrees with this layout.

## Journal: property and key hashes are type IDs (2026-11-20)

The `+0x08` words in the property graph are type/class IDs, not property names:

- Every 48-byte property node shares one hash, `0xc4e5502a` (1,641 records).
- The 32-byte key/part nodes use 58 distinct hashes. The most frequent are
  `0xd2afc0b6` (3,165), `0x6503b274` (3,043), `0xb24165eb` (2,491),
  `0xa03e7c22` (1,935), `0x114ce194` (1,935), and `0xa12c8b39` (1,641).
- None of these hashes occurs in the plaintext LSCH, PSIN, LENM, or LRSC words,
  and none matches JOAAT of the candidate class names tested so far.

They therefore form a separate type or class ID space. They should be mapped by
structure and cross-reference rather than by dictionary lookup.

## Journal: root shape classification (2026-11-20)

The 483 roots split by header flags and pointer count:

| Shape | Named | Unnamed |
| --- | ---: | ---: |
| `flags=0xffff0000`, one pointer | 306 | 79 |
| `flags=0`, one pointer | 0 | 84 |
| other flags, one or two pointers | 0 | 14 |
| `flags=0`, no pointer | 0 | 2 |

Every named vehicle root has the `0xffff0000`/one-pointer shape. The 79 unnamed
roots with the same shape are therefore vehicle-like models missing from the
name dictionary. The 84 `flags=0` roots form a distinct class.

Child signatures classify 202 vehicle-like roots as cars, 8 as bikes, 1 as an
aircraft, and 174 as unknown. The unnamed vehicle-like subset includes 13 cars,
3 bikes, and 1 aircraft; the rest have no named child parts. `tools/root_classes.py`
prints the shape and child-signature breakdown.

## Journal: flags=0 root class (2026-11-20)

The 84 `flags=0` roots use the 32-byte struct with a tagged pointer at `+0x10`,
not the vehicle root's `+0x18` pointer. Their `+0x08` type hashes group them:

| Type hash | Roots |
| --- | ---: |
| `0xb0399a69` | 44 |
| `0xd72178e2` | 15 |
| `0x1ff9fad` | 11 |
| `0x347a0e63` | 4 |
| `0xa4023631` | 4 |
| five smaller groups | 6 |

The `+0x10` word is the tagged pointer target, not a value. Their child nodes
carry their own type hashes (`0x35e28de`, `0xf7124547`, and others) and continue
as linked lists or arrays. Vehicle roots instead use `+0x08 = 0xc48ab516` and a
pointer at `+0x18`. The `flags=0` roots are therefore a different object class,
not unnamed vehicles.

## Journal: header class split and Front A comparison (2026-11-20)

The root word at `+0x04` decodes as `[u16 zero][u16 class]` in little-endian:

| High u16 | Roots | Meaning |
| ---: | ---: | --- |
| `0xffff` | 385 | vehicle-like (306 named, 79 unnamed) |
| `0` | 86 | distinct class (84 with one pointer, 2 with none) |
| `1` | 5 | other class |
| `2` | 2 | other class |
| `3` | 1 | other class |
| `5` | 2 | other class |
| `6` | 1 | other class |
| `8` | 1 | other class |

Exact bytes are `00 00 05 00` for class 1, `00 00 02 00` for class 2, and so on.
The lower u16 is zero in every root.

Direct child type IDs are disjoint by class:

| Root class | Child type IDs |
| --- | --- |
| `0xffff` | `0xc8eaca7f` (375) plus 10 singletons |
| `0` | `0x35e28de` (44), `0xee8f65ba` (15), `0x5b8ff882` (11), `0xf7124547` (4), `0x6537d3d1` (4), smaller groups |
| `1..8` | mostly `0xee8f65ba`; three class-1 roots use `0x835bda2d` |

The `0` class is therefore a distinct serialized class, not an unnamed vehicle.

Front A tables after the hypothetical 256-byte signature (`0x160..+0x08`) are
16-byte multiples but share **zero** bytes across every pair of controls, and all
171 aligned 16-byte blocks are unique. Entropy is 7.14 to 7.73. The `0x160` table
boundary is not confirmed by a common encrypted prefix; it remains a size-based
hypothesis.

## Journal: six-archive extraction and `data.rpf` (2026-11-20)

Work ran in the separate `investigate/data-rpf` worktree. All addresses below
are archive-relative and all ranges include the start and exclude the end.
The top-level samples stayed in the original checkout.

### Extraction evidence

The Rust range map and Python zlib decoder agreed on 30,527 complete zlib
streams across the six archives. The extraction records every interval in
`ranges.tsv`, with stored SHA-256 and, for zlib, the decoded SHA-256 and
offset in the output file. Opaque spans and front and trailer bytes are
saved under `raw/`. Zero runs are represented by their length and hash.
Default chains use the Rust 64 KiB continuation rule.

| Archive | zlib streams | Default chains | Raw files | Decoded bytes |
| --- | ---: | ---: | ---: | ---: |
| `appdata0.rpf` | 0 | 0 | 4 | 0 |
| `common.rpf` | 954 | 277 | 119 | 50,231,123 |
| `core_licenses_data.rpf` | 3 | 3 | 4 | 2,004 |
| `data.rpf` | 28,509 | 26,488 | 675 | 1,403,250,069 |
| `script.rpf` | 1,057 | 1,013 | 7 | 6,180,256 |
| `story000_bvh4.rpf` | 4 | 4 | 2 | 16,677 |

### Observed in `data.rpf`

- The 481,544,304-byte root has Front A at `0x60..0xf510`, Front B at
  `0xf510..0x11060`, and a trailer at `0x1cb37000..0x1cb3c870`. Header
  `+0x24` is 699. There are 41 child header candidates. Forty have a
  trailer candidate based on span length and padding within the window up
  to the next header. At `0x120d7000`, the 592-byte trailer candidate is a
  suffix of an opaque span at `0x121d59b0..0x121d5c00`. Thirteen zeros
  separate it from the preceding nonzero byte. The child at `0x1a279000`
  has no matching candidate under these rules.
- Thirteen child trailers have the same complete 29,856 bytes, with
  SHA-256 `241aa550b916d962689b57c4ae52588780c32eb30c7443ac720c8cda8d7a3e41`.
  Each corresponding header reports 1,115 in `+0x24`. Joining zlib streams
  across only the minimum zero padding to the next 16-byte boundary yields
  exactly 1,115 groups in every pack, from 1,124 to 1,135 streams per pack.
  The first PSIN object is also byte-identical in all 13 packs. The first
  resource at a page offset of `+0x10` contains the same line translated in
  each language. The independently detected order agrees with
  `core_language` in the common archive at `0xd000`. Brazilian Portuguese
  is the second pack, `0x1c2e000..0x26e24a0`. Its first localized resource
  combines two zlib streams, `0x1c44010..0x1c49605` and
  `0x1c49610..0x1c4dd46`, of 131,072 and 61,408 decoded bytes. The first
  stream size shows why the original 64 KiB rule leaves some resources split.
  The 14,495 localized groups are indexed in `localized/groups.tsv`.
- The pack candidate at `0x964000..0x9c9350` contains 156 complete raw
  DEFLATE streams, agreeing with `+0x24 = 156`. They yield 136
  `RBF0:uiCreditsPageData` objects and 20 `RBF0:uiCreditsConfig` objects,
  matching the function declared for `data/credits/credits.rpf` by
  `core_credits` at `common.rpf@0xc000`. Thirty-seven streams occupy a
  complete opaque map row. The others share opaque rows across zero
  alignment padding or consume terminal zero bytes classified as padding
  by the original map. For example, `0x966000..0x966308` yields a
  1,318-byte `uiCreditsPageData` object and a second raw DEFLATE stream
  starts at `0x966310`. The raw DEFLATE decoder validates stream termination
  and the identification uses each decoded RBF0 magic and root name. The
  raw DEFLATE format carries no checksum.
- There are 2,281 default zlib chains that start with PSIN. Of these,
  2,200 satisfy the seven-section parser and CHKS length field. Twenty-one
  more satisfy both after appending a raw tail at the next aligned address.
  For example, the chain at `0x1cab4000` decodes 2,228,224 bytes, and the
  raw tail at `0x1cb0d960..0x1cb2f340` supplies 137,696 bytes. CHKS
  declares 2,365,920 bytes, exactly the joined length.

### Interpretations and open checks

The exact trailer matches and translated content give independent evidence
for the localization pack family. The shared trailer cannot supply absolute
stored ranges by itself across these packs because their resource extents
differ. The per-pack front metadata may encode offsets, lengths or other
entry data. The names for the 13 language packs and the credits pack come
from the common manifests and payload contents. Outer index records remain
undecoded, so the nested ranges and stream groupings remain candidates for
archive entry boundaries.

### Reproduction

Run from the repository root. The commands use a dedicated directory under
`output/` so any earlier extractions in that directory remain available.

~~~sh
samples=.
out=output/range-extract
cargo build --locked --release
python3 -B tools/extract_archive_ranges.py "$samples" --output "$out"
python3 -B tools/decode_raw_deflate.py "$out"
python3 -B tools/data_rpf_inventory.py "$out/data.rpf" \
  --language-manifest "$out/common.rpf/decoded/0000d000.xml" \
  --credits-manifest "$out/common.rpf/decoded/0000c000.xml" \
  --export-from "$samples/data.rpf" > "$out/data.rpf/inventory.txt"
python3 -B tools/extract_archive_ranges.py "$samples" --output "$out" --verify
mkdir -p "$out/core_licenses_data.rpf/nested" "$out/script.rpf/nested"
target/release/rage-tools-vi extract-raw "$samples/core_licenses_data.rpf" 1000 2e50 "$out/core_licenses_data.rpf/nested/00001000.candidate.rpf"
target/release/rage-tools-vi extract-raw "$samples/script.rpf" 1000 c3b90 "$out/script.rpf/nested/00001000.candidate.rpf"
target/release/rage-tools-vi extract-raw "$samples/script.rpf" c4000 4282b0 "$out/script.rpf/nested/000c4000.candidate.rpf"
~~~

### Resource names in the large child at `0x1228e000`

The candidate extent is `0x1228e000..0x1a278990`. Its fixed header bytes
at `+0x40..+0x60` differ from the other observed `data.rpf` headers.
A scan of the 2,895 minimum-padding zlib groups whose first stream starts
at a page offset of `+0x10` found 2,502 distinct NUL-terminated resource
names backed by aligned, little-endian 64-bit pointers. Each pointer
equals `0x50000000` plus the name's decoded group offset. The names all
begin with `w_`. There are 1,075 `.#dr` names, all with the pointer at
decoded offset `0xa8`, and 1,427 `.#ft` names, with the pointer at
varying offsets.

For example, the group at `0x122da010..0x122db195` stores
`0x50001480` at decoded `+0xa8`. At decoded `+0x1480` the bytes spell
`w_ar_adb_01.#dr` followed by NUL. Neighboring strings include
`WAP_Receiver`, `Wpn_Holster`, and `Wpn_Root`. The next named group
contains `w_ar_adb_01_barrel_01.#dr`. Repeated base, `_hi`, and
`_mid` variants support a model and component collection. The full
list and decoded file paths are in the extraction's `data.rpf/resource-names.tsv`.
The internal pointers name resources inside the payload. The archive
index's filename and extent fields still require decoding.

## Journal: class-0 layout structure (2026-11-20)

The class-0 roots are layout/skeleton definitions, not vehicle models. A typical
chain is:

```text
class-0 root
  └─ child type 0x35e28de
       └─ container type 0x5387a04e, 102 pointer entries (16 B each)
            └─ bone node type 0x6503b274
                 └─ array type 0x1ebb416b
                      └─ 48-byte position records
```

Each 48-byte position record holds `[float x, float y, float z, zeros..., uint id
or flags, zeros]`. Examples from layout `0xaf83defd`:

- `(0.000757, 0.002069, 0)`
- `(-0.000921, -0.000375, -0.053436)`
- `(0, 0, -0.063312)`
- `(0, 0.010087, -0.036405)`

The 102-entry container matches a vehicle bone/seat layout. The class-0 root
names remain unmatched, but the class is structurally identified as the layout
registry. `tools/property_tree.py --id 0xaf83defd --depth 4` dumps it, including
48-byte arrays and their type hash.

## Journal: data.rpf output layout and localized text (2026-11-20)

The local data extraction now lives at `output/data.rpf/`. Each identified
language archive has an immediate child folder with its archive filename,
for example `output/data.rpf/brazilian_final.rpf/`. Text filenames use the
archive-relative start offset in hexadecimal.

The localized binaries contain object data and NUL-terminated UTF-8 strings.
In the Brazilian resource at archive offset `0x1c44010`, the `0DRPz` marker
is at decoded `+0x10` and a contiguous text run begins at decoded `+0x20000`.
The exporter checks the marker and exports runs of three or more adjacent
UTF-8 strings, with at least two containing eight or more letters. It
exported 12,546 text files across 13 language folders with 3,892,601 string
occurrences. These counts include repeats. Isolated strings and short runs
may be absent. Text is in decoded byte order. Resource keys and the text
index inside each binary still need decoding.

`localized/text.tsv` links every text file to its decoded binary and stored
range. To reproduce the current layout from the repository root with the
existing common archive XML extracts, run the following on a fresh data
output directory.

~~~sh
cargo build --locked --release
python3 -B tools/extract_archive_ranges.py data.rpf --output output
python3 -B tools/decode_raw_deflate.py output
python3 -B tools/data_rpf_inventory.py output/data.rpf \
  --language-manifest output/common.rpf/00d000.xml \
  --credits-manifest output/common.rpf/00c000.xml \
  --export-from data.rpf > output/data.rpf/inventory.txt
python3 -B tools/export_localized_text.py
~~~

## Journal: full data.rpf extraction signature scan (2026-11-20)

`file` 5.46 reported one default libmagic label for all 42,485 regular files
under `output/data.rpf/`, including manifests, the text exports, and 40 carved
RPF candidates. The report lists each relative path, file size, and label.
It excludes the report itself.

- 28,820 files were labelled generic data. All 40 carved RPFs are in this group.
- 11,395 were labelled UTF-8 text and 922 ASCII text.
- 214 received the zlib label, including 213 raw spans and one decoded
  artifact, `decoded/00c71620.bin`. The latter returned a dictionary request
  when probed with `file -z`; its payload was not verified by this scan.
- Sample spot checks confirmed misleading signatures. The structurally
  validated `mixed-psin/1b366000.bin` begins with PSIN despite its Thermocam
  label, and `polish_final.rpf/7ee0010.txt` is exported Polish UTF-8 text
  despite its OpenPGP label.

~~~sh
python3 -B tools/scan_libmagic.py output/data.rpf --report output/data.rpf/libmagic.tsv
~~~

## Journal: DOS signatures and remaining opaque spans (2026-11-20)

Of 13 DOS labels, two point to verified localized UTF-8 text exports.
Ten point to fragments from already checksum-verified zlib streams that
begin off the observed page resource starts and immediately follow another
zlib stream across minimum alignment padding. One 560-byte opaque span at
archive-relative `0x11d4e1d0..0x11d4e400` remains unresolved. Its COM label
has no independent structural support. The apparent zlib header in the
decoded `00c71620.bin` coincides with a series of little-endian virtual
pointers starting with `0x5000a848` and increasing by `0x40`.

A byte-alignment sweep for the four common zlib header pairs in all opaque
map spans produced no additional Adler-32-verified streams within the
16 MiB decoded limit. Of the 213 raw spans labelled zlib by libmagic, 167
produced a terminating raw DEFLATE decode after skipping the wrapper
header, in some cases using the preceding decoded chunk as a trial
dictionary. Their Adler-32 values did not match the stored trailer.
The other 46 did not reach a validated stream end. No purely stored PSIN
was found at a 16-byte-aligned position wholly within an opaque map span.

Allowing additional adjacent zlib chunks and full-size stored chunks
recovered four more structurally complete PSIN objects. The declared
section sizes and CHKS total length agree with each reconstructed file.
The stored ranges are archive-relative.

| Stored range | Decoded bytes |
| --- | ---: |
| `0x1a208000..0x1a24c0ae` | 629,408 |
| `0x1ad43000..0x1ad84550` | 871,992 |
| `0x1ae00000..0x1af397da` | 6,973,008 |
| `0x1b29c000..0x1b3101cb` | 2,971,984 |

The per-candidate findings are in `dos-signatures.tsv`,
`opaque-streams.tsv`, and `rejoined-psin.tsv` under `output/data.rpf/`.

~~~sh
python3 -B tools/scan_libmagic.py output/data.rpf --report output/data.rpf/libmagic.tsv
python3 -B tools/audit_opaque_streams.py
~~~

## Journal: object magics and alternate PSIN layouts (2026-11-20)

A leading `78 da` is a zlib wrapper signature. The 213 opaque candidates
from the previous entry each follow an aligned, checksum-verified zlib
stream. None of those adjacent decoded prefixes starts with a recognized
object header or carries the checked resource markers at their normal
positions. Fourteen candidates follow the archive header at
`0x120d7000` and 199 follow the header at `0x1a279000` in archive order.
These are nearest-header observations. The last child's end is unresolved.

The `0x11d4e1d0..0x11d4e400` span labelled DOS COM follows the verified
zlib stream at `0x11d4e0f0`. That stream decodes an `RBF0` object with
root `rage__fwuiAnimationNodeGraph`. The typed object is the neighbor
of the opaque span. Its type cannot be extended to the 560 opaque bytes.

Scanning decoded headers yielded 1,260 wrapped-zlib RBF0 objects with
valid root-name descriptors, plus the 156 previously recovered credits
objects from raw DEFLATE. The wrapped-zlib objects include 603
`rage__fwuiPrefab`, 190 `rage__fwuiAnimationNodeGraph`, 136
`UIScreen`, and 125 `CMovieSubtitleContainer` roots. Another 15,768
default decoded files contain `0DRPz` at decoded `+0x10`. These markers
identify object families independently of libmagic labels.

The 56 previously unverified PSIN chains are already completely decoded.
They use `PSIN PMAP PSCH PSIG [STDN|STFN] STNS CHKS`; 52 omit the
optional section, three have STDN, and one has STFN. Every section size
lands on the next header, and each CHKS total matches its file size.
The PSIN validator now recognizes these three observed sequences in
addition to the original sequence. All 2,281 PSIN-starting chains default
to complete objects or have structurally validated reconstructions
(2,256 complete and 25 rejoined). Classification used section headers and
did not interpret LSNS bodies.

~~~sh
python3 -B tools/identify_opaque_context.py
~~~

## Journal: data.rpf bone corpus names the tree (2026-11-20)

The other model's decoded `data.rpf` output contains 2,281 plaintext PSIN bone
lists. Harvesting NUL-separated identifiers from those PSIN bodies gives 3,212
unique names, saved as [tools/bone_names.txt](tools/bone_names.txt).

A JOAAT scan of the 2,702,384-byte script object against that corpus finds
**1,977 hits**, against a random expectation of 0.75. The top names are exactly
the vehicle part and bone vocabulary:

| Name | Hits |
| --- | ---: |
| `window_lf_mover` | 365 |
| `window_rf_mover` | 359 |
| `boot` | 177 |
| `window_lr_mover` | 176 |
| `window_rr_mover` | 176 |
| `bonnet` | 111 |
| `mirror_r`, `mirror_l` | 68 each |
| `door_dside_f` | 67 |
| `door_pside_f` | 59 |
| `door_dside_r` | 55 |
| `door_pside_r` | 54 |

The script tree is therefore a richly named vehicle part/attachment graph, not
just a root registry. The same corpus adds **no** new root names: running
`root_names.py --extra tools/bone_names.txt` leaves the 306/483 root count
unchanged. `tools/bone_corpus.py` reproduces the scan, either from the data
worktree or from the saved name list.

## Journal: localization extents differential (2026-11-20)

The 13 `data.rpf` localization packs give a direct differential control for the
stored-extent table. All packs have N = 1,115 and a shared 29,856-byte trailer.
Front B is fixed at **13,392 bytes = 12 × 1,115 + 12** in every pack. Front A
varies from 65,264 to 65,360 bytes. The first payload starts at pack-relative
`0x14000` in every pack.

Ordinal 0 is identical across languages: rel `0x14000`, consumed 6,995, slot
8,208, decoded 7,176. Ordinal 1 starts at rel `0x16010` in every pack, but its
consumed bytes and slot differ; the next rel is the previous rel plus the
previous slot. Over all 1,115 ordinals, pairwise equality is only 2–30 for rel,
666–806 for slot, and 66–153 for decoded bytes. The extents are therefore
per-language and sequential.

A plaintext search for rel, slot, consumed, or decoded values in Front A and
Front B finds essentially nothing. The extent tables are encrypted or
compressed. Front B's fixed 12-byte-per-entry size makes it the strongest
lookup/index candidate; Front A remains the per-language table candidate and the
trailer the shared name pool. `tools/localized_extents.py` reproduces the
comparison and the plaintext search.

## Journal: Front B large-mode size relation (2026-11-20)

Scanning all 42 `data.rpf` headers gives nine header modes. The large mode
`0x00020007 / 0x00090f02` has 14 headers and fits `align16(12 × (N+1))` in all
14; `align16(12 × N)` fits only 13. The discriminator is the N mod 4 = 0 sample
at `0x11d10000`, N = 1,168, B = 14,032 = `align16(12 × 1,169)`, not
`align16(12 × 1,168) = 14,016`. The N = 1,115 localization packs are ambiguous
because both predictions coincide. `script_large` (mode `0x00020006 /
0x00090f02`) also fits N+1: N = 1,012, B = 12,160 = `align16(12 × 1,013)`, not
12,144.

Other modes do not follow either 12N prediction. The small mode `0x00010005 /
0x00090f01` fits 12N in only 2 of 14 headers, and the data root N = 699 mode
`0x00010007 / 0x00090f02` is far short. The large-mode Front B is therefore
`12 × (N+1)` bytes, consistent with a 12-byte header or sentinel row followed by
N records.

The A/B equality matrix for american, brazilian, and german shows no common
prefix or suffix, zero equal 16-byte blocks at the same index or after shifts,
and byte equality at chance (0.24–0.46%). The cipher and field placement remain
open. The measured size relation is recorded; acceptance still requires a
decoded record that predicts a held-out stored extent.

## Journal: Front B mode table closed (2026-11-20)

Adding the 10N residual completes the size-mode table. The small controls fit
`align16(10N)`: story and core N = 4 give 48; core embedded, appdata0, script
root, and script small N = 2 give 32. The data root N = 699 gives B = 6,992 =
`align16(10N)`. The common N = 418 case also gives B = 4,192 = `align16(10N)`.
The small `0x00010005 / 0x00090f01` mode fits 10N in 6 of 14 data.rpf headers;
12N fits only 2.

The large localization mode fits 12N in 13 of 14 and 12(N+1) in 14 of 14. The
discriminator is N = 1,168 at `0x11d10000`; script_large also fits 12(N+1).
All 13 localization packs share N = 1,115, so that is a cohort observation, not
a size law across N. The A/B equality matrix still shows no shared prefix,
suffix, or aligned 16-byte block.

The metadata size handoff is closed at this measured relation. No further blind
byte scans are planned. Indexed extraction is parked pending independent framing,
key material, or a decoded field; the next active track is class, wrapper, and
transform analysis.

## Journal: Front B size-rule limitation (2026-11-20)

The data review notes an important limit: the discriminating counts N = 1,168
and N = 1,012 are both N mod 4 = 0. For those counts, `12 × (N+1)` and a rule
with one extra 16-byte pad or terminal row coincide. The measured large-mode
residual is therefore real, but a 12-byte header/sentinel remains a hypothesis.
A same-mode sample with N mod 4 = 1 or 2 would distinguish the size rules. No
such sample is present in the current cohort, so metadata inference stays closed
at the measured relation and indexed extraction remains parked.

## Journal: +0x10 wrapper probe (2026-11-20)

The 32-byte records whose only tagged pointer is at `+0x10` are a distinct
forwarding class: 12,332 wrappers, 7,960 direct leaf targets, and **zero** direct
rotation leaves (`0xfc86dde2`). The positive control sits in the `+0x18`
named-part population instead: 1,230 direct rotation targets, including
`door_dside_r` -> `0x1a3e60`, `door_pside_f` -> `0x1a4490`, and `door_dside_f`
-> `0x1a45a0`.

The wrapper population splits by its `+0x08` word and target size:

| Raw `+0x08` | Wrappers | Leaf targets | Rotation | Target sizes | Named parents |
| --- | ---: | ---: | ---: | --- | ---: |
| `0x6503b274` | 3,043 | 3,043 | 0 | 144/192/240/336 arrays | 0 |
| `0xb24165eb` | 2,491 | 2,491 | 0 | 64/112/80/128 | 0 |
| `0x114ce194` | 1,935 | 1,935 | 0 | 144/176/208/112 | 0 |
| `0x363061d6` | 186 | 186 | 0 | 144/96/48 | 0 |
| `0xc8eaca7f` | 46 | 46 | 0 | 48 | 44 |

The `0xc8eaca7f` family is the vehicle-root forwarder; the other families forward
to anonymous arrays. A train/test split by root parity has no positive rotation
examples, so no predictive rotation signature exists in this population. The
wrapper does not name the layout; its raw tag selects the target family.

`tools/wrapper_probe.py` writes `output/script.rpf/wrapper-probe.tsv` and
`output/script.rpf/part-rotation-controls.tsv`. The wrapper class is closed:
`+0x10` forwards to type-tagged arrays and leaves, while rotations live under
`+0x18` named parts.

## Journal: +0x18 rotation-parts test (2026-11-20)

The `+0x18` 32-byte population has 3,540 records: 305 roots, 1,953 named parts,
and 1,282 unnamed records. It has 1,230 direct leaf targets, and **all 1,230 are
rotation leaves** with tag `0xfc86dde2`; there are zero negative leaf targets.
The remaining direct targets are non-leaf: 1,935 carry word `0xa03e7c22` and 375
carry `0xc8eaca7f` at `+0x08`. The leaf tag is therefore the only reliable
discriminator in this population.

The parent-field predictor is degenerate: with no negative leaves, every parent
field (`kind`, `parent_name`, `parent_size`, `parent_layout`, `parent_h08`,
`part_h08`, `parent_field`) appears perfect. It cannot distinguish rotation from
non-rotation. The non-leaf/unknown control is the `airbus` root 12772 at
`0x1a4710`, whose target `0x1a4730` has `target_word8 = 0xc8eaca7f` and is not a
leaf.

Known parts:

| Part | Part offset | Target offset | Tag | Angle word | Angle |
| --- | ---: | ---: | --- | ---: | ---: |
| `boot` (airbus) | `0x1a5130` | `0x1a5150` | `0xfc86dde2` | `0xbfc91687` | -1.571 |
| `bonnet` (airtug) | `0x1a5c40` | `0x1a5c60` | `0xfc86dde2` | `0x3f860a96` | 1.0472 |

Repeated part names across roots show both general and vehicle-specific angles:
`boot` (177 roots) clusters at -1.25664, -1.5708, -1.309, and -1.13446;
`bonnet` (111 roots) at 1.0472, 1.309, 1.047, and -1.25664. By contrast,
`door_dside_f` is 0.0 in 62/67 roots, `door_pside_f` is 0.0 in 57/59, and
`winder_lf_mover` is -6.283 in 45/47. The angle is neither one global constant nor
purely vehicle-specific.

`tools/rotation_parts.py` writes `output/script.rpf/rotation-parts.tsv` and
`rotation-pairs.tsv`. This closes the current wrapper/rotation round; array
element semantics and class-0 enumeration remain separate.

## Journal: no named-vehicle-to-class-0 layout link (2026-11-20)

Tested sources for an independent vehicle → class-0 layout reference:

- `common.rpf` XML: 259 files, **0** `<layout>` tags, 1,980 `<vehicleModelName>`
  tags. The model-name fields are UI/task identifiers and do not pair with a
  layout field.
- Decoded `data.rpf`: 0 files containing `<layout>`, `vehiclelayouts`, or
  `CVehicleLayout`. The decoded PSIN files carry bone lists, not model-layout
  definitions.
- Structured external `vehicles.meta`: 3 files, 27 model/layout pairs, 17
  distinct layout names, 108 normalized JOAAT variants (exact, lower, upper,
  stripped `LAYOUT_`, and prefixed forms). None matches any of the 86 class-0
  roots, and none matches any of the 483 roots.

Nonmatch control: `swift2` → `LAYOUT_HELI_SWIFT2`, JOAAT(lower) `0x2d07aba0`,
not a class-0 root and not any root. The shared bone list remains supporting
evidence only; it is not an independent link.

`tools/layout_link_probe.py` writes `output/script.rpf/layout-links.tsv`.

## Journal: expanded native texture extraction (2026-11-20)

Scanning all 29,888 decoded `data.rpf` resources for the texture-dictionary
header found 89 candidates. Of these, 73 validate as native texture
dictionaries and 16 are other resource dictionaries. The valid set contains
**788 textures totaling 306,008,064 bytes**. Every record validates its
parallel JOAAT name hash, dimensions, format code, stride, graphics pointer,
and `count × stride` bounds.

The export is at `output/data.rpf/textures-expanded/manifest.tsv` with 788
files under `files/`. Dimensions include 4×128 through 2048×1024, and format
codes 0x47, 0x4D, and 0x62. The data workstream's four-control set is a subset.

The shader marker scan is negative. An exact scan of the decoded corpus finds
no `DXBC`, `DXIL`, SPIR-V magic, `DDS `, `GNF `, or KTX marker. The earlier grep
hits were Portuguese localization text: `0241c010.bin` contains `PLMDDS` and
`SUSPIRO`; the other matches were binary-regex false positives. The common.rpf
SPS1 catalog contains shader names only; no compiled shader has been verified.
LSNS/encrypted material was not touched.

`tools/native_texture_scan.py` reproduces the scan and export.

## Journal: top-mip texture decode trial (2026-11-20)

Small control: `loading_screen_spinner_i1` (32×32, format 0x4D, 4,096 stored
bytes). The best-looking candidate is top-mip offset `0x800` with 4×4-block
tiles (16×16-pixel tiles), decoded as BC3; it renders a plausible circular
spinner. The PNG is saved with the other samples.

Holdout: `hud_i8d6` (128×128) and `hud_i689` (256×32), same format. Offsets
`0`, `0x2000`, `0x4000`, `0x6000` and block tiles `1`, `2`, `4`, `8` were
tested. None renders a coherent HUD image. Descriptor dimensions, format code,
graphics pointer, and `count × stride` bounds agree, so the failure is in
layout or codec, not in the descriptor bounds.

Bounded unknowns: the top-mip offset and mip order, the row pitch, the tile
order, and the actual codec for format 0x4D. Format 0x62 remains unsupported by
this decoder. No conversion is labelled verified; the spinner remains a
candidate and the HUD holdout is unresolved.

`tools/texture_decode.py` writes the linear and tiled candidates to
`output/textures-verify` in the worktree; the reviewed PNGs were
copied to `output/textures-verify` in main.

## Journal: typed array headers and class-0 48-byte entries (2026-11-20)

The no-pointer records are typed arrays, not one fixed 16-byte layout. The
48-byte header stores the used count at `+0x14`, the element stride at `+0x18`,
and the element type hash at `+0x28`. The body is `count × stride`, followed by
fewer than 16 bytes of alignment padding. Validating that relation finds 7,894
arrays across strides 4, 8, 12, 16, 32, and 48.

| Type tag | Stride | Arrays | Entries | Entry observation |
| --- | ---: | ---: | ---: | --- |
| `0x1ebb416b` | 48 | 3,043 | 15,732 | vec3, 20 zero bytes, u32 at `+0x20`, 12 zero bytes |
| `0x8f18aff0` | 8 | 2,491 | 7,630 | u32 hash plus f32 |
| `0xb066759f` | 32 | 1,935 | 4,365 | eight words |
| `0xb1ee00d0` | 48 | 166 | 294 | zeros, vec3 at `+0x10`, u32 at `+0x20` |
| `0xc92cdeca` | 16 | 82 | 2,605 | `vector3`: three floats plus pad |
| `0x0000000f` | 4 | 93 | 1,646 | single floats |
| `0x2ff4ac04` | 12 | 4 | 6 | three packed floats |

`0xc92cdeca` is exactly `JOAAT("vector3")`. This is the first array type hash
matched to an independent name and confirms that `+0x28` is a type hash. The 82
vector3 arrays have 17, 21, and other entry counts; 12 are planar (`y = 0`).

The `0x1ebb416b` arrays are all under 44 class-0 roots of type `0xb0399a69`.
Each u32 at `+0x20` is `[high:8][index:8]`: the index is 0..49 and the high byte
is 0, 1, or 2; 141 distinct IDs occur. Per root, 19 to 34 of the 50 indices
occur. Of 3,043 arrays, 2,208 contain at least one high-1/high-2 pair for the
same index (4,650 pairs). The paired vec3 values differ by 0 to 3.18 units, with
median 0.065 and 216 identical pairs. This is consistent with paired endpoints,
two transform layers, or two sides, but the evidence does not distinguish them.
The entries are not 3x4 matrices: only the first three floats are populated.

The `0x8f18aff0` pairs contain 252 distinct hash words; none matches the 3,212
data bone names, the XML/token dictionary, or the 2,502 resource names. The
`0xb066759f` and `0xb1ee00d0` layouts still need field-level assignment.

Tools added in this workstream: `tools/array_types.py` (generic header decode),
`tools/type_tags.py` (JOAAT type-tag match), `tools/value_entries.py` (16-byte
entry classifier), `tools/value_array_context.py` (root class/type context), and
`tools/transform_pairs.py` (high-1/high-2 pairing).

## Journal: class-0 bone tables (2026-11-20)

Each of the 44 class-0 roots with point arrays has one `0x5387a04e` table. The
hierarchy is `class-0 root` (class 0, type `0xb0399a69`) -> `0x35e28de` node ->
`0x5387a04e` table -> `0x6503b274` bone node -> `0x1ebb416b` point array.

There are 44 tables, 3,043 entries, and exactly 3,043 point arrays. Each
16-byte table entry is a name hash, zero, a tagged pointer, and `0x71717171`.
Every target is a 32-byte `0x6503b274` node that points to a `0x1ebb416b` array.
Table sizes vary from 4 to 155; roots 0 and 209 have 102 entries, and one root
has 96.

The table hash namespace has 612 values, shared across roots. The
`0x8f18aff0` pair namespace has 252 values, 57 of which overlap the table
hashes. No table hash matches JOAAT, CRC32, FNV-1a, FNV-1, djb2, or sdbm over
381k XML, bone, and resource-name candidates. The hash algorithm and names
remain open.

`tools/bone_table.py` flattens the hierarchy to `handoff/script-bones.tsv`
(3,043 rows): root, table, bone index/hash, bone node, point array, point count,
and first point/ID.

## Journal: two object families (2026-11-20)

The typed arrays separate into two root families. The class-0 bone-table roots
have type `0xb0399a69`: 44 roots, `0x5387a04e` tables, and `0x1ebb416b` point
arrays. The `0x8f18aff0` hash/f32 arrays sit under a different family: 25 roots
of type `0xd72178e2`, spanning classes 0, 1, 2, 3, 5, 6, and 8. The
`0xc92cdeca` vector3 arrays also use type `0xd72178e2` roots (38 roots). Neither
family has a named ancestor in the current JOAAT dictionaries.

The 57 hashes shared by the bone tables and the `0x8f18aff0` pairs may be a
shared name namespace or shared field names; the current evidence does not
assign a meaning. Keep the skeleton family and the type-`0xd72178e2` family
separate when decoding.

## Journal: 48-byte entry has two vec3 slots (2026-11-20)

The `0x1ebb416b` entry is not a 3x4 matrix. It has a vec3 at `+0x00`, a second
vec3 at `+0x10`, a u32 at `+0x20`, and zero padding. Of 15,732 entries, 10,895
have only the first vec3, 3,704 have both vec3 slots populated, and 1,133 are
zero. The two-vector entries have segment lengths from 0 to 4.44, median 0.035
and p90 0.396; 431 point pairs coincide within an array at 1e-6 tolerance.

This is consistent with bone geometry made of points and segments, not a
transform matrix. The u32 remains `[high:8][index:8]` with index 0..49. The
first vec3 is already exported in `handoff/script-bones.tsv`; the second vec3
and the point/edge classification are not yet in the handoff.

Update: `handoff/script-bone-points.tsv` now exports all 15,732 entries with both
vec3 slots, the u32 ID, and the point/edge/zero classification.

## Journal: class-0 skeleton template families (2026-11-20)

The 44 class-0 roots do not have 44 unrelated skeletons. Grouping their bone-hash
sets by exact equality gives 38 groups, but near-identical sets reveal templates.
With a Jaccard threshold of 0.75, the roots collapse into **16 families**.

| Family | Roots | Bones/root | Core hashes | Union |
| --- | ---: | ---: | ---: | ---: |
| F01 | 12 | 76–107 | 51 | 112 |
| F02 | 10 | 40–66 | 40 | 66 |
| F03 | 4 | 116–134 | 101 | 155 |
| F04 | 2 | 133–155 | 132 | 156 |
| F05 | 2 | 67–71 | 65 | 73 |
| F06 | 2 | 31–34 | 30 | 35 |
| F07 | 2 | 22–24 | 22 | 24 |
| F08 | 2 | 4 | 4 | 4 |
| F09–F16 | 1 each | 2–133 | all | all |

The core hashes are the stable part of each template; the variable hashes are
optional bones or variants. The two large families account for 22 of the 44
roots. This is structural evidence for a small skeleton catalogue, but the
template names and the 612-hash namespace remain open.

Artifacts: `handoff/script-bone-geometry.tsv` (3,043 rows),
`handoff/script-bone-templates.tsv` (exact sets), and
`handoff/script-bone-template-families.tsv` (16 families).

Geometry hints for the families (hypotheses, not names):

| Family | Avg root bbox (x, y, z) | Hint |
| --- | --- | --- |
| F02 | 0.44, 0.20, 0.95 | narrow and long; weapon-like candidate |
| F03 | 3.00, 2.43, 2.57 | large; vehicle/trailer-like candidate |
| F04 | 1.85, 1.97, 3.46 | large and long; vehicle/trailer-like candidate |
| F01 | 1.08, 0.74, 1.22 | medium; ped/vehicle candidate unresolved |
| F07, F10–F12 | 0.16–0.68 | small; weapon component or prop candidate |
| F08 | 0.00, 0.51, 0.013 | flat; plane/decal candidate |
| F16 | 0.003, 0.003, 0.231 | thin; line/bone candidate |

These are shape heuristics only. A name or a data-side model/layout match is
still required before assigning an asset class.

## Journal: vehicle mover curves (2026-11-20)

The `0xb066759f` arrays are vehicle-specific curves, not generic geometry. They
appear under **244 named vehicle roots** and contain **1,935 curve arrays** with
**36 distinct channel keys**.

Each array uses stride 32. An entry is `[t, 0, 0, 0, 0, y, z, 0]`; the first
float is the normalized parameter and the second vec4 carries the path offset.
The channel key is stored on the ancestor node of type `0xd2afc0b6` at `+0x10`.

Named channels (JOAAT of public vehicle bone names):

| Key | Name | Curves | Roots |
| --- | --- | ---: | ---: |
| `0x86d36840` | `window_lf_mover` | 319 | 174 |
| `0x031fd5fc` | `window_rf_mover` | 317 | 173 |
| `0x6ec686bf` | `window_lr_mover` | 148 | 83 |
| `0xfc0ce3f6` | `window_rr_mover` | 148 | 83 |
| `0xe179bcee` | `door_dside_r` | 2 | 2 |
| `0x41628d75` | `door_pside_r` | 2 | 2 |

Four unnamed channels occur in roughly 200 roots each
(`0xfbdba1a6`, `0xeaeecb7b`, `0x8bb5d91e`, `0x552ea55`). Their curve shapes
suggest standard door, bonnet, boot, or seat movers, but the names are not yet
matched.

Artifact: `handoff/script-vehicle-curves.tsv` (1,935 rows).

Channel behavior across the 1,935 curves:

| Key | Curves | Roots | Avg Δy | Avg Δz | Behavior hint |
| --- | ---: | ---: | ---: | ---: | --- |
| `0xfbdba1a6` | 231 | 230 | 0.120 | 1.473 | large vertical travel; bonnet/boot-like |
| `0x8bb5d91e` | 217 | 216 | 0.110 | 1.360 | large vertical travel; bonnet/boot-like |
| `0xeaeecb7b` | 221 | 221 | 0.051 | 0.119 | small travel; door/seat/handle-like |
| `0x0552ea55` | 202 | 201 | 0.043 | 0.108 | small travel; door/seat/handle-like |
| `0x87d29d26` | 26 | 26 | 0.087 | 2.531 | large vertical travel; suspension/tipper-like |
| `0x66ec13b0` | 23 | 16 | 0.386 | 0.011 | lateral travel; door/hatch-like |

The two large-z channels occur in almost every vehicle, which makes bonnet and
boot the strongest hypothesis; the two small-travel channels remain consistent
with doors, seats, or handles. These are behavior hints, not JOAAT matches.

## Journal: vehicle-root inventory (2026-11-20)

The class-`0xffff` vehicle-like roots are now inventoried. There are **385**
such roots; **306** have a JOAAT name, and **244** carry mover curves. The
remaining **141** have no curve array (some are non-vehicle class-0xffff roots,
some are vehicles without animated movers).

Artifact: `handoff/script-vehicles.tsv` (root record, root ID/name, flags,
curve count, channel hashes). This gives the join key between named vehicles and
the curve data; the next test is a data.rpf model/layout match.

## Journal: class-0 skeleton family name comparison (2026-11-20)

Data reproduced the core and union hash counts for all 16 families. JOAAT of
2,502 decoded `data.rpf` resource names and their stems, in original and
lowercase spelling, matched none of the 44 roots or 612 unique bone hashes.
JOAAT of 3,212 PSIN names also matched none of the bone hashes. An independently
decoded skeleton with an ordered bone table is needed to validate names and
bone order. Bus answer `#0071` closed request `#0067`.

Reproduction and results are in the data worktree under
`tools/data_skeleton_family_links.py` and `handoff/data-skeleton-family-links.tsv`.

## Journal: data-side skeleton-family negative (2026-11-20)

The data workstream answered request `#0067` with a negative mapping. It
recomputed all 16 family core/union sets and reproduced every recorded count.
It found:

- 0 of 44 roots match JOAAT of the 2,502 pointed `data.rpf` resource names or
  stems (original and lowercase);
- 0 of 612 bone hashes match those names/stems;
- 0 of 612 bone hashes match the 3,212 harvested PSIN names.

Geometry remains the only support for F02/F07 being narrow and F03/F04 being
large. A verified mapping needs an independently decoded ordered skeleton.

Evidence: `handoff/data-skeleton-family-links.tsv` and
`handoff/data-skeleton-family-status.md`.

## Journal: same-root curve/part join (2026-11-20)

Data suggested joining the four unnamed curve keys to independently named part
nodes and rotation leaves in the same vehicle root. The first pass is negative
for name hashes and named parts:

- 0 of 1,935 curves have their key hash as a non-key-node name inside the same
  root;
- 0 of 1,935 curves have a named part matching the key name or its `_mover`
  base;
- the known positive controls (`window_lf_mover`, etc.) also give 0, so the
  simple name join does not validate.

The test root `astron` has 119 subtree records but only two named entries:
`astron` and `boot`; window/bonnet part names are not present there. The key
hash lives in the `0xd2afc0b6` key node, not in a part node. Rotation-leaf
counts are retained per root for the next geometric join.

Artifact: `handoff/script-vehicle-curve-join.tsv` (1,935 rows).

## Journal: vehicle curve branch calibration (2026-11-20)

The known window controls have two curves per key in `astron`. The branch split
is consistent:

| Channel | Outer branch end | Inner branch end |
| --- | --- | --- |
| `window_lf_mover` | y=+0.104, z=-0.398 | y=-0.111, z=-0.011 |
| `window_rf_mover` | y=+0.104, z=-0.398 | y=+0.111, z=+0.011 |
| `window_lr_mover` | y=+0.044, z=-0.283 | y=-0.082, z=-0.009 |
| `window_rr_mover` | y=+0.044, z=-0.283 | y=+0.082, z=+0.009 |

The outer branch carries the large z travel and is identical across left/right.
The inner branch has zero/small z and its y sign separates left from right:
left channels are negative, right channels are positive.

The four unnamed channels form two persistent pairs:

- pair A: `0xfbdba1a6`, `0x8bb5d91e`;
- pair B: `0xeaeecb7b`, `0x0552ea55`.

On `216cstreamer`, pair A ends at z=-1.396 and pair B at z=+1.396 (equal within
each pair). On `airbus`, the pair members have opposite z signs, with magnitudes
1.396 and 1.431. This is a symmetric four-mover pattern, not a simple
bonnet/boot pair. It is consistent with four doors, gear doors, or another
paired symmetric mechanism; the names remain open.

Artifact: `handoff/script-vehicle-branch-relations.tsv`.

## Journal: vehicle curves are angular (2026-11-20)

The y/z curve channels are angles, not positional offsets. Testing every curve
endpoint in degrees:

- all 3,870 endpoints have a residual below 0.5° to an integer degree;
- 5,651 of 6,298 sampled points have an exact 0.0° residual;
- 1.396 rad = 80.0° and 1.431 rad = 82.0°, matching the data-side observation.

The same-root leaf-angle match is weak and does not beat the shuffled baseline
(y: 264/1,935 vs 374/1,935; z: 478/1,935 vs 773/1,935), so there is no verified
leaf identity yet. The angular test succeeds, so the pivot/axis positional join
is not the next step. The four unnamed channels are symmetric angular movers;
the positional bonnet/boot interpretation is withdrawn.

Artifacts: `handoff/script-vehicle-curve-angles.tsv` and
`tools/vehicle_curve_angles.py`.

Correction: the angular claim does not survive the discriminator test. The
native-precision, deduplicated nonzero samples have residual rates at 1.0°,
0.5°, and 0.25° grids that match a random-offset baseline (for example, y at
1.0°: 0.108 observed vs 0.101 baseline). The earlier "<0.5°" statement was
tautological. Same-root leaf matches are 727/6,539 (0.1112), below the seeded
cross-root permutation mean 0.1151 and p95 0.1191.

The angular-units hypothesis is therefore **unverified**; the positional
interpretation was also unverified. The four unnamed channels stay parked until
a decoded schema or a named mover link exists. Superseding artifact:
`handoff/script-vehicle-curve-quantization.tsv`; superseding tool:
`tools/vehicle_curve_quantization.py`. The old `vehicle_curve_angles.py` and
`script-vehicle-curve-angles.tsv` are removed.

## Journal: vehicle-curve naming closed (2026-11-20)

Data closed the four-channel test in `#0081`: leave names and units open, and
do not prioritize a geometric join. The existing corpus cannot identify a
vehicle skeleton or layout independently. Reopen only with a decoded
`0xb066759f` field schema or a named model mover with an independently verified
path or angle. Data returned to direct-inotify standby. No requests remain open.

Array-inventory correction: the complete validation includes empty arrays
(`count = 0`) whose stride is larger than the zero-byte body. The earlier
7,894 total omitted 66 such arrays. The authoritative inventory is **7,960
typed arrays across 396 roots**; types and strides are unchanged otherwise.
Artifact: `handoff/script-array-inventory.tsv`; tool:
`tools/array_inventory.py`. `tools/array_types.py` now accepts zero-count arrays.

## Journal: remaining 0xb1ee00d0 arrays (2026-11-20)

The complete inventory resolves the remaining large point-array variant:
**186 arrays, 4 class-0 roots, 294 entries**. The roots are class 0, type
`0x347a0e63`. Entry counts are 0 (20 arrays), 1 (38), and 2 (128). Of 294
entries, 210 are the sparse `vec3+pad+id` form and 84 carry a second vec3
(`f32x12`).

The layout is a sibling of `0x1ebb416b`: both use 48-byte entries and a u32 id
at `+0x20`, but `0xb1ee00d0` places the primary vec3 at `+0x10` rather than
`+0x00`. Semantics and names remain open; no further scan is justified without
a model/layout crib.

## Journal: 0x8f18aff0 arrays are normalized weights (2026-11-20)

The `0x8f18aff0` arrays are not arbitrary `(hash, f32)` pairs. Grouping by array
and summing the f32 values gives:

- arrays: 2,491; pairs: 7,630;
- sum min = 0.9999, median = 1.0, max = 1.0000017;
- **all 2,491 arrays sum to 1.0** within float precision;
- pair counts range from 1 to 10; 252 distinct hash words;
- 57 of the 252 hashes overlap the class-0 bone-table namespace.

This is a normalized weight distribution keyed by hash. The most likely
interpretation is skin/part weights, but the hash names are not yet resolved.
Artifacts: `handoff/script-pair-arrays.tsv` and `tools/pair_arrays.py`.

## Journal: extraction-first baseline and quadtree (2026-11-20)

Priority moved to extraction-first with a quadtree view. The normalized
inventory covers `data.rpf` contiguously (481,544,304 stored bytes; 57,651
ranges) and the two known `script.rpf` ranges. Repo-wide totals: 57,653 ranges,
482,337,669 stored bytes, 1,405,952,453 decoded bytes.

The general entry point `tools/extract_entry.py` wraps the Rust `extract`,
`extract-zlib`, and `extract-raw` commands, writes create-new outputs, and logs
sha256/byte counts. Verified: script object 2,702,384 bytes
`592afd44…c3c82`; blob 331,728 bytes `b5d622ca…dc28e`; data.rpf
`0x12330..0x12548` 1,288 bytes `7e341292…b5234`, matching the manifest.

The quadtree builds 44 resource-local trees from `script-bone-geometry.tsv`:
3,007 valid XY items, 36 `points=0` rows excluded, 412 flat extents retained.
Split-spanning items stay at the current node. Tools/artifacts:
`tools/extraction_inventory.py`, `tools/extract_entry.py`,
`tools/quadtree.py`, `handoff/extraction-inventory-summary.tsv`,
`handoff/script-quadtree-summary.tsv`.

Coverage completion: the small and large archives are now fully mapped. Adding
`shaders.rpf` (18,686 spans; 411,695,600 bytes; 275,540,780 decoded) and
`textures.rpf` (5,581 spans; 192,585,024 bytes; 161,086,752 decoded) brings the
repo-wide range inventory to **86,029 ranges**, **1,096,854,128 stored bytes**,
**1,896,307,661 decoded bytes**, and **429,764,784 unclassified bytes**. Every
local archive is 100% covered at the range layer. Unclassified bytes remain
semantic work, not missing coverage.

Unclassified-gap triage: 6,111 spans / 429,764,784 bytes. Largest archives:
shaders 5,253 spans / 273,959,915 bytes (largest 1,483,917 at `0xcb27d00`);
textures 59 / 136,021,963 (largest 27,997,847 at `0x53d3240`); data 673 /
19,130,746 (largest 1,131,248 at `0x1a8a01e0`); script 5 / 431,696, including
the parked 331,728-byte blob. Artifacts: `handoff/unclassified-summary.tsv`,
`handoff/unclassified-gaps.md`, `tools/coverage_gaps.py`.

Extraction entry-point verification matrix: six cases pass. script object
(2,702,384; `592afd44…`), script blob (331,728; `b5d622ca…`), data zlib
(1,288; `7e341292…`), data unclassified raw (816; `1133e8d0…`), common zlib
(65,536; `15c3a3f5…`), story zlib (800; `e20f1cc6…`). Artifact:
`handoff/extraction-entry-verification.tsv`; tool:
`tools/verify_extraction.py`.

Quadtree verification: 44 roots, 3,007 unique items, 36 placeholders excluded,
412 flat extents, zero duplicates/missing/extra items, zero structural failures.
Artifacts: `tools/verify_quadtree.py`,
`handoff/script-quadtree-verification.tsv`.

## Journal: first extraction milestone delivered (2026-11-20)

Integrator delivered the containment viewer in `4dc3f05`: all 8 local archives,
86,029 ranges, 36,640 emitted files with drill-down/back, and archive-level
browsing for data/textures. Pack tiles appear where bounded inference completed;
translation is deferred. Script side contributes the inventory, entry point,
unclassified triage, six-case verification, and the separate bone quadtree
(44 roots / 3,007 items, 8/8 verification). Protocol remains in standby.

## Journal: downloads corpus boundary (2026-11-20)

The supplied source tree has 22 RPF9 files / 161,307,137,472 bytes. Eight match
repo samples byte-for-byte; fourteen are source packs. Six smaller packs are
copied under `output/downloads-corpus` and owned by the integrator. Script will
not duplicate those extraction jobs. Inventory:
`handoff/downloads-corpus-inventory.tsv`.

## Downloaded source inventory (2026-11-20)

The source directory contains 108 files. All 22 files with the RPF extension
carry the RPF9 signature and total 161,307,137,472 stored bytes. All eight repo
samples matched their source files byte for byte. Six additional nested RPFs
were range-extracted and passed source and output hash verification. The 14
archives with extraction manifests cover 3,542,353,632 source bytes. The eight
larger RPFs are cataloged. Output is local under `output/downloads-corpus/`.

Downloads corpus update: the six nested packs passed range/output
verification in `f37b99f`, bringing coverage to 14/22 archives and 3,542,353,632
source bytes. The remaining eight archives total 157,764,783,840 bytes; the
workspace volume has 81 GiB free. Integrator index:
`output/downloads-corpus/index.html`.

## Large archive index pilot (2026-11-20)

Indexed anim.rpf in place with tools/stream_index.py in 38.25 s, using
53,772 KiB peak RSS. The TSV has 258,150 contiguous intervals spanning
4,407,626,384 source bytes. Its 130,509 checksum-valid zlib streams account
for 4,188,160,838 stored bytes and 11,572,883,428 decoded bytes. Gaps total
219,436,634 bytes; the remaining bytes are the front and trailer. Nine streams
distributed through the archive were independently inflated and hashed.
On common.rpf all 954 stream bounds and digests matched the verified manifest.

## Journal: anim.rpf large-archive pilot (2026-11-20)

`map anim.rpf` completed in 3m49s at 4,340,508 KiB peak RSS: 259,138 spans,
130,509 zlib ranges, 11,572,883,428 decoded bytes, 37,742,843 unclassified, and
100% coverage. A bounded `mmap` extraction of `0x6000..0x62dc` used 15,428 KiB
and 0.0s, matching the Rust output sha256
`cbdb4e9d1ecbe7ff0a197f759c47c0c5f0f88ebb0830ee6af958ef6949b430e4`.
The Rust extractor used 4.31 GB RSS for the same range.

Blocker: `fs::read()` materializes the archive; a streaming index scanner is
required for `levels.rpf` (76 GB) on a 29 GB machine. Proposed order:
anim, packs, navmeshes, core_bvh4, movies, story000, audio, levels.
Artifacts: `handoff/anim-index-pilot.md`, `tools/mmap_extract.py`.

Streaming-index follow-up: `tools/stream_index.py` completed `anim.rpf` in
29.08s at 333,272 KiB peak RSS, with 258,152 spans, 130,510 zlib streams, and
11,593,461,732 decoded bytes. It found a valid stream at
`0xed61e010..0xee4ff55f` decoding 20,578,304 bytes, which the Rust path missed
because `MAX_PAYLOAD_SIZE = 16 MiB`. This is a coverage bug separate from the
full-file `fs::read()` memory issue.

Full-speed bulk extraction: `tools/bulk_extract.py` validated on common.rpf
(954 streams, 50,231,123 bytes, 0.11s) and run on packs.rpf: 144,366 streams,
9,735,393,283 decoded, 16 workers, 576.72s, 5,332,044 KiB RSS. Output:
`output/extracted/packs` (144,366 files,
9.4 GB). Manifest count and decoded total match the index. Artifact:
`handoff/bulk-extraction-status.tsv`.

Packs signature survey: 144,366 streams classified. Dominant `u16_4042`
(28,713 / 5,434,544,304 bytes), then binary 113,480 / 4,247,446,132,
`0f000080` 1,148, PSIN 586, XML? 386, zero 47, zlib 5, RBF0 1. The two dominant
headers are still unnamed; they are the next semantic target.

`u16_4042` probe: 28,713 streams, 2,992 sizes. Large classes are 64 KiB
multiples (393,216; 131,072; 851,968; 196,608; 262,144; 327,680; 65,536;
524,288; 458,752). Header words after `0x4042` recur in low-byte families
0x21/0x26/0x28/0x25 and are not plausible offsets. The 1,040-byte group is
byte-identical across at least eight streams. Hypothesis: low byte is a
type/class tag; payload class (texture/audio) remains open.

`0f000080` probe: 1,148 streams / 11,692,416 bytes; almost all 9.9–10.1 KiB.
Header `0x8000000f`, count-like 0x62a and 0x6b5..bc, then packed data; entropy
6.9 and full-range 16-bit values. Hypothesis: compact quantized geometry/navmesh
or animation; name open.

`u16_4042` size-class behavior: 1,040/256 are metadata-like (entropy 2.8–3.0,
zero 0.57–0.63); 393,216/851,968/524,288 are high-entropy (7.97–7.98, zero
0.003–0.004); 131,072/196,608/262,144/65,536 are structured (entropy 5.2–6.2,
zero 0.30–0.44). The family mixes metadata and packed/structured payloads;
texture/audio/geometry remains undecided.

## Journal: packs semantic checkpoint saved (2026-11-20)

The packs extraction and semantic survey are persisted in
`handoff/packs-semantic-log.md`. Extraction: 144,366 streams /
9,735,393,283 decoded; 0 missing/extra/failures. Signature families:
binary 113,480; `u16_4042` 28,713; `0f000080` 1,148; PSIN 586; XML 386.
`u16_4042` splits into metadata-like, high-entropy, and structured size classes;
`0f000080` is compact high-entropy (~6.9), likely quantized geometry/animation.
All probe tools and TSV artifacts are saved.

ML binary clustering pilot: 113,480 `binary` streams, 32 MiniBatchKMeans
clusters over byte features after stripping leading zeros. Largest families are
zero-prefixed `...0050` tables; visible subgroups include `GM_U01_C` (`474d5f55`),
`0x4040`, `0e000080`, and float-like headers. This is a proposal engine, not a
verifier. Artifacts: `handoff/packs-binary-clusters.md` /
`handoff/packs-binary-clusters.tsv`; tool `tools/ml_binary_clusters.py`;
requirements `requirements-ml.txt`.

Active-learning queue: `handoff/packs-label-queue.tsv`, 128 representatives
(four variants per ML cluster), with empty `label` fields. Generator:
`tools/active_learning_queue.py`. Labels feed the supervised classifier; the
deterministic verifier remains ground truth.

Extraction relocation: `packs` (144,366 / 9.4 GB) and `anim` (130,510 / 11 GB)
were moved to `output/extracted/` on the NVMe repo disk. Manifests were rewritten
to local paths and both `verify_bulk.py` rows PASS. The Mammoth output copies
were removed after verification; the RPF source stays on Mammoth. Bulk runner
now uses batches, `madvise`, incremental manifests, and `--resume`.

## Journal: audio.rpf AWC extraction (2026-11-20)

`audio.rpf` is an Xbox build. The large unclassified span contains real
**AWC/ADAT** containers, not zlib streams. A read-only ADAT scan extracted
**6,625 containers / 23,510,389,456 bytes** with per-container SHA-256.

Header observations: version 1, flags `0xff21`, 6–24 streams, consistent
`data_offset`; chunk types `0x55` data, `0x36` peak, `0xA3` seektable, and
`0x76` format/stream chunk. `0x76` carries 48000 Hz and sample-count-like
fields; data chunks are multiples of 2048.

Decode is **not** solved. `vgmstream` rejects the AWC variant. Reconstructed
XMA2 WAV (ffmpeg) reaches the xma2 decoder but fails with
`channel len > samples_per_frame`; XMA1, byte-swapped XMA2, and alternate block
alignments fail too. The next requirement is the GTA VI `0x76`/stream-info
layout or the codec key/format, not another blind XMA2 wrapper.
Artifact: `handoff/audio-awc.md`; tool: `tools/extract_awc.py`.

## Journal: GTA VI AWC framing and Bink/XMA2 tests (2026-11-21)

The GTA VI AWC container is a new `ADAT` layout, not the GTA V AWC layout that
vgmstream parses. Header: `u16` version 1 at `+0x04`, `u16` flags `0xff21` at
`+0x06`, `u16` streams at `+0x08`, `u32` data offset at `+0x0c`, `u16[streams]`
chunk indexes at `+0x10`, and a `u64` chunk table from `0x50` to `data_offset`.
The chunk packing remains `type:8 / size:28 / offset:28`.

The `0x76` format chunk is 32 bytes: sample count at `+0x00` and `+0x0c`,
sample rate at `+0x08`, an unknown `u16` at `+0x0a` (probably
peak/headroom/block metric), codec ID at `+0x1c`, codec sub-ID at `+0x1d`, and
zero at `+0x1e`. `tools/awc_framing.py --limit 0` parsed **2,320 parsed stream rows**
from the 6,625 containers into `handoff/audio-awc-framing.tsv`: codec `0x0b`
2,081, `0x05` 166, `0x02` 73; rates 48,000 (2,143), 32,000 (165), 12,000 (10),
28,000 (1), 32,016 (1); sub-IDs `0x01` 2,025 and `0x02` 295. This disproves the
earlier “all streams are 0x0B/48k” assumption.

A real framing signal surfaced: many 2,048-byte `0x55` data chunks begin with
`a0 00 f8` and repeat those bytes at offset **162**. 1,451 streams show the
`0,162` pair; 840 have no marker in the first 16 hits, 23 have one, and six
larger streams repeat the pattern `162,...,162,266,162,...`. The marker is not
a fixed prefix; it is a packet/frame boundary candidate.

Decode attempts this session:

- vgmstream's AWC parser rejects the new header, as expected.
- `tools/test_awc_xma2.py` builds a proper `XMA2WAVEFORMATEX` WAVE around each
  `0x55` chunk and tries mono/stereo and encoder versions. ffmpeg reaches the
  XMA2 decoder but emits silence or low-level artifacts; no tonal speech.
- `tools/bruteforce_ueba.py` builds an `ABEU` v1 header and wraps payloads as
  `[0x9999][u16 size][payload]`. vgmstream accepts the synthetic container and
  reports `RAD Game tools Bink Audio`. A whole chunk yields a ~90 ms burst then
  zeros; splitting at 2,048/1,024/512 bytes yields silence. The 5,140-candidate
  offset sweep produced only three non-silent bursts; the best flatness 0.189 /
  harmonic 0.619 was a transient, not continuous audio.

Current interpretation: the container and `0x76` metadata are usable, and the
codec is not GTA V XMA2/Vorbis/Opus directly. `0x0B` is new; `Bink2Scarlett.dll`
and the UEBA path make **Bink Audio 2** the strongest hypothesis, but it is not
proven while payloads decode to transients. The next concrete test is splitting
at the `a0 00 f8`/162 marker and rebuilding the `0x76` codec header. If that
still yields silence, test whether `0x55` is AWC/XXTEA-encrypted; GTA V has an
encrypted-data flag and `.awckey`, and no GTA VI key was found in the sampled
build tree.

Artifacts: `handoff/audio-awc.md`, `handoff/audio-awc-decode.md`,
`handoff/audio-awc-framing.tsv`, `tools/awc_framing.py`,
`tools/bruteforce_ueba.py`, `tools/test_awc_xma2.py`.

## Journal: AWC codec 0x05 decoded as XMA2 (2026-11-21)

The first XMA2 wrapper used `wFormatTag=0x0161`, which is **WMAudio2**. ffmpeg
therefore called the WMA decoder and produced silence/noise; the XMA2 path was
never actually exercised. The correct XMA2 format tag is `0x0166`. With that
tag, the 32-bit 32 kHz streams under AWC codec `0x05` decode to continuous
audio.

`tools/extract_awc_xma2.py` now selects codec-`0x05` rows from
`handoff/audio-awc-framing.tsv`, builds a real `XMA2WAVEFORMATEX` RIFF around
each `0x55` data chunk, and decodes with ffmpeg:

- 166 codec-`0x05` rows selected; **151 unique streams decoded to PCM WAV**,
  86 MB total.
- 15 rows are fragmented/misparsed AWC entries with no recoverable stream; the
  manifest records them explicitly. These are not decoder failures.
- All 151 outputs are non-silent; **148 have spectral flatness < 0.1**.
- Example `000000069dbc6000` stream 0: 5.5 s at 32 kHz, RMS 0.234, flatness
  0.038, harmonic 0.398. The spectrogram is continuous with low-frequency
  harmonic structure, not a single decoder transient.
- Local manifest: `output/extracted/audio-xma2/manifest.tsv`.

This is the **first non-zlib codec family decoded from `audio.rpf`**. The
earlier conclusion that all AWC payloads were undecodable was caused by the
wrong format tag, not by encryption.

Remaining audio work: `0x0B` is still the Bink Audio 2/UEBA hypothesis and
`0x02` is unresolved. The `a0 00 f8` / 162-byte marker remains the framing lead
for `0x0B`; AWC/XXTEA encryption is only a fallback if marker splitting fails.
Artifacts: `handoff/audio-awc.md`, `handoff/audio-awc-decode.md`,
`tools/extract_awc_xma2.py`, `tools/test_awc_xma2.py`.

## Journal: consolidate collaboration docs, remove obsolete audit (2026-11-21)

The collaboration protocol now lives in `AGENTS.md`; the separate `COLLAB.md`
was removed and its ownership, merge, and handoff rules were merged into the
single workstreams section. Only `main` remains active.

`pi-payload-audit.md` was removed as an obsolete pre-collaboration attempt; the
reproducible tool `tools/pi_archive_audit.py` remains. The earlier journal
reference to the removed audit file is historical and is not rewritten.

## Journal: AWC codec 0x0B decoded as Opus (2026-11-21)

`data` reported the bounded result in bus #0126. A rerun on the three
documented AWC files reproduced six mono and two stereo streams decoded with
libopus at 48 kHz. Each `0x800`-byte block in chunk `0x55` starts with a
little-endian 16-bit packet size at `+0x00` and an Opus TOC at `+0x02`. The
next length field is `2 + packet_size` bytes after the current length field.
Zero bytes pad the rest of the block. In the mono control, `a0 00 f8` is a
160-byte packet containing one 20 ms mono fullband CELT frame. The observed
162-byte stride follows from the length field; later packet sizes vary.

In `000000000129b000.awc`, stream 0 occupies the AWC-relative range
`[0x4a80, 0x6280)`. Its 66 packets produce 63,360 frames. The `0xA3` table
reports `0, 23040, 48000, 62400`: the first three entries are storage-block
starts and the last is the final packet start. All eight streams match this
rule in units of decoded frames times channels. The tested payloads decode
directly without decryption. The UEBA transient came from feeding Opus to the
Bink decoder. The declared mono sample count is 60,741; exact pre-skip and
end-trim are still open.

The separate `0x02` control contains six streams. All but one word per stream
are finite as little-endian float32. The exceptional word `0xfffface1` always
occurs 2,048 words before the declared end. This supports a float-valued
payload with internal structure; its format remains open.

Reproduction commands and control files are listed in
`handoff/data-awc-opus.md`. Tool: `tools/data_awc_opus_probe.py`.

## Journal: Opus trim bounds and AWC 0x02 ACE1 trailer (2026-11-21)

Bus #0129 reported controls for trim and trailer structure. Reproduced by
generating mono and stereo control WAVs from `tools/data_awc_opus_probe.py`
and running `tools/data_awc_trim_controls.py` on both sets. The declared
count `N` at `0x76 +0x00` is consistent with `N / C` target frames, where
`C` is channels. For `T` decoded frames the total trim is `T - N / C`.
The first mono and stereo controls give 2,619 and 2,017 frames respectively.
Exact-zero spans vary across the controls, and the seek table ends at the
last packet start. The measured data leave the initial skip `P` in the
inclusive range `0..T - N / C`, so the aligned range `[P, P + N / C)` is
undetermined. Keep decoded PCM untrimmed and preserve the counts.

Reproduced `--ace1` on both control files. All 12 streams have `4 × N`
payload bytes. The last `0x2000` bytes start with the LE magic
`0xfffface1` followed by fifteen LE `u16` pairs at `[+0x04, +0x40)` and
zero padding. The last pair predicts the number of `0x2000`-byte blocks
of finite LE float32 words in the prefix. For the first control stream,
the prefix occupies AWC-relative `[0x800, 0x26800)` and the trailer
occupies `[0x26800, 0x28800)`. The pair meanings and signal encoding remain
open. Controls and commands are in `handoff/data-awc-trim-ace1.md`.

## Journal: bulk AWC Opus export (2026-11-21)

The lead reported the completed export in bus #0130. The local manifest
`output/extracted/audio-opus/manifest.tsv` contains 2,081 stream rows and
2,067 WAV hashes. The export directory occupies 2.5 GiB on disk. Counting
the error rows directly gives 11 unsupported-rate entries (ten 12 kHz and
one 28 kHz), two seek mismatches (one with an empty table), and one stream
rejected as wholly silent. The preliminary bus breakdown gave ten rate
entries and three seek mismatches. The total number of exceptions is 14.
The manifest records the declared sample count. Channel count and decoded
frame count are available in each untrimmed WAV header.

Reproduce the export from the repository root with
`python3 -B tools/extract_awc_opus.py`. The driver selects source containers
from `handoff/audio-awc-framing.tsv`.

## Journal: AWC 0x02 ACE1 impulse responses reconstructed (2026-11-21)

Bus #0132 identified the `0x02` float data as overlapping half-spectra of
2,048-point real FFT windows. Each `0x2000`-byte tile stores 1,024 complex
little-endian float32 bins and omits Nyquist. The windows advance 1,024
samples. A zero first half fixes the first Nyquist amplitude; the shared
halves fix each subsequent amplitude. Concatenate the reconstructed second
halves except the final window and keep the tap count at `0x76 +0x0c`.

Rerunning `tools/data_awc_ace1_ir.py` on `0000000697c43000.awc` and
`0000000697d6c000.awc` reproduced all 12 controls. Tap counts are 420,
31,400, and 117,991. Overlap disagreement and end padding are each below
`8e-9` RMS throughout. `ffprobe` confirmed the 117,991-tap WAV is mono
48 kHz `pcm_f32le`. The first values of the trailer pairs still lack a
verified interpretation. The exact inverse-transform formulas, commands,
and local WAV paths are in `handoff/data-awc-ace1-ir.md`.

## Journal: bulk audio export complete (2026-11-21)

The lead exported all three AWC codec families from the rebuilt containers:

- **`0x05` XMA2:** 151/166 streams, 86 MB PCM WAV.
- **`0x0B` Opus:** 2,067/2,081 streams, 2.5 GB untrimmed PCM WAV. Block framing
  is `[u16le size][Opus packet]` inside each `0x800`-byte data block; the
  `a0 00 f8` / 162-marker is the 160-byte packet plus its two-byte length.
- **`0x02` ACE1:** 73/73 streams, 6 MB float32 impulse-response WAV. Each
  `0x2000` tile is half of a 2,048-point real FFT; the ACE1 trailer starts with
  `0xfffface1`. All controls reconstruct with overlap/padding RMS < 8e-9.

Opus exceptions are explicit: 11 sample-rate entries (10×12 kHz, 1×28 kHz),
2 seek mismatches, and 1 silent stream. Exact Opus pre-skip/end-trim remains
open; bulk WAVs are deliberately untrimmed. The first ACE1 trailer pair values
are also unassigned.

Artifacts: `handoff/audio-opus-decode.tsv`, `handoff/audio-ace1-decode.tsv`,
`tools/extract_awc_opus.py`, `tools/extract_awc_ace1.py`,
`handoff/data-awc-opus.md`, `handoff/data-awc-ace1-ir.md`. The reproducible
runner is `tools/rebuild_audio.sh`; it now expects 151 XMA2, 2,067 Opus, and
73 ACE1 WAVs.

## Journal: all 14 Opus export exceptions decoded (2026-11-21)

Reran the bounded `tools/data_opus_exceptions.py` probe from bus #0136.
All 14 rows parsed and decoded at 48 kHz. The 11 streams with nominal
12 or 28 kHz descriptors have seek tables on the 48 kHz decode clock.
Optional nominal-rate copies resample the PCM. Sequential decoding also
produced 29,760 frames for `00000001126d9000.awc` stream 2 with an
inconsistent seek table, and 50,880 for `000000027dcd2000.awc` stream 0
without a seek table. `00000002f5c82000.awc` stream 0 contains 62 identical
`fc ff fe` packets and valid stereo silence. Its 59,520 zero frames agree
with the seek entries.

The 14 supplemental untrimmed WAVs in `output/extracted/audio-opus-exceptions/`
complete the 2,081-stream export together with the initial 2,067 WAVs.
That supplemental directory also contains 11 optional resampled copies.
Exact trim and runtime seek handling for the two seek exceptions are open.
Commands and per-case limits are in `handoff/data-awc-opus-exceptions.md`.

## Journal: Opus exception rows normalized (2026-11-21)

The 14 rows that the first bulk pass rejected were replayed independently and
all are valid Opus. They are now part of the primary export, not a side folder:

- 11 non-48 kHz sources (10×12 kHz, 1×28 kHz) decode at 48 kHz; the source rate
  is retained in the manifest.
- 5 seek flags remain (3 terminal mismatches, 1 mismatch, 1 missing); the
  sequential untrimmed PCM is preserved.
- 1 stream is valid encoded stereo silence (`fc ff fe` packets) and is preserved.

Final `0x0B` export: **2,081/2,081 WAVs, 2.5 GiB, zero decode failures**.
This supersedes the earlier 2,067/2,081 count in the previous journal entry.
Artifacts: `handoff/audio-opus-decode.tsv`, `tools/extract_awc_opus.py`,
`handoff/data-awc-opus-exceptions.md`.

## Journal: read-only extraction pilot for audio and levels (2026-11-21)

Built `tools/extraction_pilot.py`, a local read-only HTTP browser over the
rebuilt corpus. It joins `output/index/audio.tsv` to the verified
`output/extracted/audio/manifest.tsv` and `output/verification.tsv`, and reads
`output/index/levels.tsv` without extracting payloads. Pages are bounded at 100
ranges; uncertain pack membership stays at archive level.

Validation: `audio.rpf` `0x5000..0x6316` resolves to extracted manifest SHA-256
`725398e5f5267e1da78a82b8582a68950d72c3dc8adb0d97b54eda40274c19f2`;
`levels.rpf` `0x1d000..0x1d701` matches the index and reports `indexed-only`
with no extracted file; `/archive?name=levels&page=1000` returns HTTP 200.
No reindex, bulk extraction, or payload copy was performed.

Command: `python3 tools/extraction_pilot.py --port 8766` (open
`http://127.0.0.1:8766/`). Report: `handoff/extraction-pilot.md`.

## Journal: static extraction pilot adopted (2026-11-21)

Data produced the static, read-only pilot `tools/extraction_index_pilot.py`;
it supersedes the temporary local HTTP server. The generator joins the audio
index to the verified manifest, checks the decoded file's size and SHA-256,
and emits bounded first/middle/last sample pages for the 2,199,213-range
`levels.rpf` index. The static artifact is
`output/extraction-index-pilot/index.html` (602 KB).

Validation output: audio `0x5000..0x6316` matched SHA-256
`725398e5f5267e1da78a82b8582a68950d72c3dc8adb0d97b54eda40274c19f2`;
levels `0x1d000..0x1d701` matched the index with no bulk extraction manifest.
No reindex or payload extraction was performed. The Playwright drill-down
verifier is present but its dependency is not installed in the base image.
Report: `handoff/extraction-pilot.md`.

## Journal: standalone extraction pilot browser check (2026-11-21)

Used the locally cached Playwright installation to exercise the final HTML in
headless Chromium. Both archive roots, all three range statuses, the audio
hash, the levels extent, and Back to the root passed. The verifier opens the
standalone artifact directly. With Playwright available to Node, reproduce
from the repository root with `node tools/verify_extraction_index_pilot.cjs`.

`data` independently ran the same Chromium check and accepted the pilot in
bus #0142. Both runs used the cached Playwright package without installation.
