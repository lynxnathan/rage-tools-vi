# Collaboration protocol

Both workstreams share one repository and one `main` branch. The goal is to keep
`main` clean, avoid overlapping edits, and exchange results as data rather than
prose.

## Cost and role split

- **Script/integrator (this harness) does the grunt work:** bulk scans, extraction,
  normalization, tooling, candidate generation, docs, and integration.
- **Data/high-cost model provides the overall picture:** architecture, format
  interpretation, cross-archive hypotheses, priority calls, and validation. It
  should not run long scans. In dual-session standby, both sides use the
  blocking inotify watcher.
- If the high-cost model needs a scan, it writes a one-paragraph request; the
  script side runs it and returns a compact table.
- Batch one request/answer per cycle. Skip idle pings.
- In dual-session standby, `bus.py wait --as <name> --since <id>` blocks on
  direct inotify delivery. Run it as a background tool process and keep it
  alive across harness yields. Use `--timeout` for an active deadline only.
  Inotify setup failures are reported explicitly.
- One driver/owner per active request. `claim`/`release` only for actual
  overlap. If an owner is blocked on the other side, report the dependency.

## Bus

The visible channel is an append-only JSONL log at
`BUS_DIR/messages.jsonl`, driven by
`tools/bus.py`.

```sh
python3 tools/bus.py digest --as data
python3 tools/bus.py read --as data
python3 tools/bus.py send --from data --to script --kind answer --body "..."
python3 tools/bus.py log
```

`digest` shows open requests and short new messages. It closes a request only
on a terminal `answer` or `handoff` (and legacy `result`); linked `note`,
`working`, and `NO_ACK` replies leave it open. `read` prints full bodies. `log`
prints the whole bus. the operator can inject messages as `operator`.

For quick work the result is the acknowledgment. For longer work send one
compact `working` update after starting, with an ETA if known; update only when
the ETA changes, work is blocked, or the sender asks. Do not acknowledge an
acknowledgment. The lead tracks a five-minute acknowledgment deadline and
records one `NO_ACK` note if it expires; the request stays open and the worker
starts immediately.

## Worktrees

| Worktree | Branch | Owner | Scope |
| --- | --- | --- | --- |
| `REPO_ROOT` | `main` | integrator | Integration, shared docs, merge target |
| `SCRIPT_WORKTREE` | `investigate/script-graph` | script workstream (grunt + integration) | `script.rpf` object graph, RPF9 metadata, Front A/cipher |
| `DATA_WORKTREE` | `investigate/data-rpf` | data workstream (overall picture) | `data.rpf`, localization, model/bone/layout semantics |

The samples (`*.rpf`) and `output/` are local and untracked. Symlink or copy them
into each worktree; never commit them.

## Ownership

- `main` integrator owns `plan.md`, `AGENTS.md`, `investigation.md`, and
  `shared/`. Only the integrator merges to `main`.
- The script workstream owns `tools/script_*`, `plan-script.md`,
  `investigation-script.md`, and `handoff/script-*`.
- The data workstream owns `output/data.rpf/`, `tools/data_*`, `plan-data.md`,
  `investigation-data.md`, and `handoff/data-*`.
- Do not edit another workstream's files. Add a new file instead of changing a
  shared tool in place.

## Shared interface

Publish handoffs as TSV files under `handoff/`:

- `data-model-bones.tsv` — model name, model hash, bone list, layout
- `data-layouts.tsv` — layout hash, layout name, entry/bone mapping
- `data-names.tsv` — hash, name, kind, source, confidence
- `data-localization.tsv` — key, language, text
- `script-roots.tsv` — root hash, name, class, source
- `script-types.tsv` — type/class ID, role, evidence

Each workstream also keeps `handoff/<stream>-status.md` with four sections:
**Done**, **Artifacts**, **Needs**, and **Next**.

## Merge rules

- Both worktrees merge `main` before starting work and before committing.
- No direct commits to `main` from a worktree.
- Workstream commits use `script:` or `data:` prefixes; docs use `docs:`.
- On a conflict in `plan.md` or `AGENTS.md`, keep `main`'s version and move the
  workstream detail into its own plan/journal.
- Append-only journals are per workstream. `investigation.md` is the integrated
  main journal; new workstream evidence goes to `investigation-script.md` or
  `investigation-data.md`, and the integrator summarizes it in `plan.md`.
- Commit early and often; uncommitted work is not shared.

## Current handoff

The script workstream needs from data:

- model name ↔ bone-list mapping, including vehicle and trailer models
- `vehiclelayouts` / layout names and hashes
- decoded localization keys/strings and the bone-hash algorithm

The data workstream needs from script:

- hash → name registry for roots and vehicle parts
- RPF9 metadata/Front A findings and any recovered index records
- class/type IDs relevant to model and layout records
