#!/usr/bin/env python3
"""Append a branch's `investigation.md` addition to the current journal.

The journal is append-only, so a contribution branch that adds a section at the old
end of the file conflicts with every later entry. This takes the added lines from
`base..tip` for `investigation.md` and appends them to the working-tree copy,
leaving existing text untouched.

    # resolve a conflicted merge: keep ours, then append the branch's section
    git checkout --ours investigation.md
    python3 tools/journal_append.py 49c8aaa pr-2

The script refuses to append a block that is already present, so re-running it after
a partial merge is safe.
"""

import argparse
import subprocess
import sys
from pathlib import Path

JOURNAL = "investigation.md"


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True,
                          text=True).stdout


def added_block(base, tip):
    """Lines the branch adds to the journal, without the diff markers."""
    patch = git("diff", "--unified=0", base, tip, "--", JOURNAL)
    lines = []
    for line in patch.splitlines():
        if line.startswith(("+++", "---", "@@", "diff ", "index ")):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="commit before the branch's journal entry")
    parser.add_argument("tip", help="branch head")
    parser.add_argument("--journal", type=Path, default=Path(JOURNAL))
    args = parser.parse_args()

    block = added_block(args.base, args.tip)
    while block and not block[0].strip():
        block.pop(0)
    if not block:
        print(f"{args.tip} adds nothing to {args.journal}")
        return 0

    current = args.journal.read_text()
    if block[0] in current:
        print(f"section already present: {block[0].strip()!r}")
        return 0

    text = current.rstrip("\n") + "\n\n" + "\n".join(block).rstrip("\n") + "\n"
    args.journal.write_text(text)
    print(f"appended {len(block)} lines to {args.journal}: {block[0].strip()!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
