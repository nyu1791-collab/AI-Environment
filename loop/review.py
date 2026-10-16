"""List agent deliverables for review. Read-only: never commits or pushes.

Usage: python3 loop/review.py <council_root>
Prints one line per agent with which deliverables exist and their size.
"""
from __future__ import annotations

import sys
from pathlib import Path

FILES = ("proposal.md", "critique.md", "vote.md", "RESULT.md")


def summarize(root: Path) -> list[dict]:
    rows = []
    for agent in sorted(p for p in root.iterdir() if p.is_dir()):
        row = {"agent": agent.name}
        for name in FILES:
            f = agent / name
            row[name] = f.stat().st_size if f.exists() and f.stat().st_size > 0 else 0
        rows.append(row)
    return rows


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    root = Path(argv[1])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1
    for row in summarize(root):
        cells = " ".join(f"{n.split('.')[0]}={row[n]}" for n in FILES)
        print(f"{row['agent']:<16} {cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
