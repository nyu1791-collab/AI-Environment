"""Append-only run ledger with a hash chain.

Each entry stores the hash of the previous entry, so an edit or deletion in the
middle of the file is detected by verify(). Used to record every agent run.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


def _digest(prev: str, body: dict) -> str:
    payload = prev + json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append(path: Path, event: dict) -> str:
    """Append one event and return its hash."""
    prev = last_hash(path)
    body = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **event}
    h = _digest(prev, body)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"hash": h, "prev": prev, "body": body}, ensure_ascii=False) + "\n")
    return h


def last_hash(path: Path) -> str:
    if not path.exists():
        return "0" * 64
    last = ""
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = line
    return json.loads(last)["hash"] if last else "0" * 64


def verify(path: Path) -> tuple[bool, int]:
    """Return (ok, number_of_entries). ok is False at the first broken link."""
    prev = "0" * 64
    count = 0
    if not path.exists():
        return True, 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry["prev"] != prev or _digest(prev, entry["body"]) != entry["hash"]:
                return False, count
            prev = entry["hash"]
            count += 1
    return True, count
