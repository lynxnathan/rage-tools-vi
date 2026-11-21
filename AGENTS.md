# Rage Tools VI investigation

Working agreements for this repository. New standing instructions from the operator
are appended here.

## Standing directives

- 2026-11-20: Save every working analysis script in `tools/`. Do not leave a
  successful one-off script only in shell history or an inline heredoc.
- 2026-11-20: Keep the roadmap, todo, and current state in `plan.md`.
  `investigation.md` is an append-only journal; append new evidence at the end
  instead of rewriting existing entries.
- 2026-11-20: When a task could use two Codex sessions and the mode is unclear,
  ask the operator whether this is a dual-session run before setting up the second
  workstream. If the operator already chose the mode, proceed with that choice.
- 2026-11-20: In dual-session mode, both sessions keep their turns open and
  wait on the bus between and after handoffs until the operator interrupts or ends
  the run.
- 2026-11-20: In dual-session standby, block on an inotify subscription to
  the bus directory. Keep that subscriber alive when the harness yields.
- 2026-11-20: Negotiate acknowledgment, progress, and result timing per
  bus message when needed.
- 2026-11-20: The lead waits up to five minutes for acknowledgment of an
  active handoff. If none arrives, record `NO_ACK` for that handoff once.
  This is a lead-side deadline. The worker starts when they receive the work.
- Future standing instructions from the operator are appended to this section.

## Tooling

- Save every analysis script that works in `tools/` before reporting its result.
  Do not leave a successful one-off script only in shell history or an inline
  heredoc.
- Make tools reproducible from the repository root, for example
  `python3 tools/root_names.py`.
- Prefer standalone Python tools with `argparse` and clear tabular output. Share
  helpers only when it reduces duplication.
- Update the relevant command block in a new journal entry or in the tool table
  in `plan.md` when adding a tool.

## Workstreams

- `main` at `REPO_ROOT` is integration only. It owns
  `plan.md`, `AGENTS.md`, `investigation.md`, `COLLAB.md`, and merges.
- Script work happens in `SCRIPT_WORKTREE` on
  `investigate/script-graph`. It owns `tools/script_*`, `plan-script.md`,
  `investigation-script.md`, and `handoff/script-*`.
- Data work happens in `DATA_WORKTREE` on
  `investigate/data-rpf`. It owns `output/data.rpf/`, `tools/data_*`,
  `plan-data.md`, `investigation-data.md`, and `handoff/data-*`.
- **Grunt work belongs to the script/integrator side:** bulk scans, extraction,
  normalization, candidate generation, and tooling. **The high-cost data model
  provides the overall picture:** architecture, format interpretation,
  cross-archive hypotheses, priority calls, and validation. It should not run
  long scans. Bus waiting follows the dual-session instructions below.
- Workstreams keep their own plan/journal. The integrator summarizes verified
  results into `plan.md` and `investigation.md` after merge. Do not edit another
  workstream's files.

## Bus

- The visible cross-workstream channel is
  `BUS_DIR/messages.jsonl`, driven by
  `tools/bus.py`.
- At the start of a turn, run
  `python3 tools/bus.py digest --as script` (or `--as data`) and answer open
  requests. Use `read --as <name>` for full bodies and `send` for replies.
- Check the bus again before ending a turn or posting a final report. In
  dual-session mode, report completed work on the bus and continue waiting.
- Do not use hidden RPC. The user can read, tail, or inject messages as
  `operator` at any time.
- Batch one request or answer per cycle. Answers should point at artifact paths
  and include a three-line summary.
- For standby use `bus.py wait --as <name> --since <id>` as a background
  tool process. It exits 0 on delivery. Use `--timeout` only for an active
  deadline. At that deadline it exits 2.
- The subscriber reads once after registration, then on a messages.jsonl
  event or IN_Q_OVERFLOW. Cursor writes do not trigger a read. Inotify
  failure is reported explicitly.
- `digest` closes a request only on a terminal `answer` or `handoff` (and
  legacy `result`). A linked `note`, `working`, or `NO_ACK` reply leaves the
  request open.
- Use English for all bus messages.

### Dual-session setup

- Confirm the two active sessions, their worktrees, and which one is `script`
  and which one is `data`. Check `git worktree list` for the actual paths.
  Use English for every bus message.
- Start with one digest per turn. Use `read --since <id-before-request>` when
  the digest has already marked a message seen. Attach replies with
  `send --reply-to <id>`. Send the result or decision directly on the bus
  with artifact paths so the operator does not have to relay it.
- Throughout a dual-session run, both sessions keep their turns open. The
  inotify subscriber blocks until an event. A harness yield leaves the
  subscriber alive without rereading the log or sending an idle ping.
- Negotiate acknowledgment, progress, and result timing per message when it
  matters. The sender can request when they need an acknowledgment or update.
  The receiver can accept or counter with an ETA for that request. For quick
  work, the result is the acknowledgment. For longer work, send one compact
  `working` update after starting, with an ETA if known. Send another update
  only when the agreed timing changes, work is blocked, or the sender asked for
  it. Do not acknowledge acknowledgments. Use local artifact links for bulk
  evidence.
- For each active handoff, the lead tracks the acknowledgment deadline from
  dispatch, up to five minutes. A result or `working` update counts as an
  acknowledgment. If none arrives by the deadline, record one `NO_ACK` note
  with the request ID and keep the request open for a later reply. The worker
  does not wait five minutes to start or to report that work has begun.
- One driver/owner per active request. Use `claim` and `release` only if
  overlapping work actually occurs. If an open request's owner is blocked on
  the other side, report that dependency instead of silently waiting.
- The JSONL bus stores messages. It cannot start a new turn in an idle
  session. Confirm that both turns are active before relying on automatic
  handoffs. If a session is unavailable, tell the operator which side could not be
  reached.

## Documentation

- `plan.md` is the current roadmap, todo, and state. Keep it current.
- `investigation.md` is an append-only journal. Add new evidence as dated
  entries at the end. Do not rewrite or reorganize existing entries.
- `format.md` documents the CLI report formats.

## Evidence

- Append results to `investigation.md` as journal entries, separating verified
  observations from hypotheses and review suggestions. Put status changes and
  next actions in `plan.md`.
- Ranges are start-inclusive and end-exclusive. State whether an offset is
  archive-relative or pack-relative.
- Keep samples, extracted output, and generated artifacts local. Do not upload
  them.
- A confirmed archive entry requires a decoded record that independently
  predicts a verified payload byte range.

## Current leads

- Object tree: JOAAT names, 306 of 483 roots named, 136 struct groups over 81
  sizes.
- Schema: LSCH/PSIN expose `x`, `y`, `z`, `datatype`, `name`, `flags`, `item`.
- Front A milestone testbed: `story000_bvh4.rpf`, which has four exact XML
  ranges.
- The 331,728-byte script blob is parked until PC launch; it does not block the
  forest or `common.rpf` work.
