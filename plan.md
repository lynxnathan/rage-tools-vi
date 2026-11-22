# Plan

Live check/todo list only. **No findings, no measurements, no explanations
here** — those live in [investigation.md](investigation.md) and `handoff/`.
Completed items leave this file.

Last updated: 2026-11-21.

## Now

- [ ] Finish the `core_bvh4` descriptor inventory: add the basis rows and cover
  `shared_minigame000_bvh4`.
- [ ] Name the remaining ped-rig bone hashes.
- [ ] Open the unnamed hash universe with a new name source.
- [ ] Repoint `tools/extraction_inventory.py` at the manifests.
- [ ] Rehash all of `levels`.

## Next

- [ ] Test the `0x8f18aff0` weight hashes against rig names.
- [ ] Re-index the eight large archives for `chain_start`.
- [ ] Validate the skeleton families against the decoded rig.
- [ ] Map the type/class IDs and transforms.
- [ ] Resolve the unnamed object roots.
- [ ] Name the unclassified payload bytes.
- [ ] Packs active-learning queue.
- [ ] ACE1 trailer pairs.
- [ ] Locate compiled shader bytecode.
- [ ] Script object root field roles.
- [ ] Verify any proposed entry record against exact ranges.

## Blocked

Each needs a specific input, not more effort.

- [ ] Directory/virtual rows in the entry count — needs Front B key material or a crib.
- [ ] Multi-chain entry grouping — needs a decoded per-entry marker.
- [ ] Front B table `S` — same mask problem.
- [ ] 9→10 byte stride boundary — needs a pack at N = 255 or 256.
- [ ] `+0x50` profiles as cipher parameters — needs a crib or key material.
- [ ] Front A milestone on `story000_bvh4.rpf` — needs independent table framing.
- [ ] Exact end of the last `data.rpf` child — needs an independent trailer start.
- [ ] Multi-mip texture tail — needs a multi-mip dictionary.
- [ ] The 331,728-byte `script.rpf` blob — needs a PC launch or a new sample.
- [ ] Full RPF9 metadata key recovery — needs key material or a second build.

## Not mine

- [ ] `explorer/` — owned by another session.
