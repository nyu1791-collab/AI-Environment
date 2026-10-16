#!/usr/bin/env python3
"""Read-only checks before a separately authorized GitHub push."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

REPOSITORY = "nyu1791-collab/AI-Environment"
BRANCH = "codex/autonomous-loop"
ROOT = Path(__file__).resolve().parents[1]


class CheckError(RuntimeError):
    pass


def command(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, timeout=20, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise CheckError(f"{args[0]} timed out; inspect remote state before retrying") from exc
    except OSError as exc:
        raise CheckError(f"{args[0]} is unavailable") from exc
    if result.returncode:
        # Never echo raw tool output: it may contain credentials or private URLs.
        raise CheckError(f"{args[0]} check failed (exit {result.returncode}); check installation/access/authentication")
    return result.stdout.strip()


def validate_target(branch: str, remote: str) -> None:
    if branch != BRANCH:
        raise CheckError(f"expected branch {BRANCH}")
    allowed = {
        f"https://github.com/{REPOSITORY}.git",
        f"https://github.com/{REPOSITORY}",
        f"git@github.com:{REPOSITORY}.git",
    }
    if remote not in allowed:
        raise CheckError("origin differs from the approved repository or includes unsupported credentials")


def validate_metadata(data: dict, allow_public: bool) -> None:
    if data.get("nameWithOwner") != REPOSITORY:
        raise CheckError("GitHub returned a different repository")
    if data.get("viewerPermission") not in {"WRITE", "MAINTAIN", "ADMIN"}:
        raise CheckError("GitHub write permission is unavailable")
    if not isinstance(data.get("isPrivate"), bool):
        raise CheckError("repository visibility could not be verified")
    if not data["isPrivate"] and not allow_public:
        raise CheckError("public repository requires explicit user approval and --allow-public")


def check(allow_public: bool = False, require_clean: bool = False) -> dict:
    branch = command(["git", "branch", "--show-current"])
    # Check fetch and push destinations separately; pushurl can differ from origin.
    remote = command(["git", "remote", "get-url", "--all", "origin"])
    push_remote = command(["git", "remote", "get-url", "--push", "--all", "origin"])
    validate_target(branch, remote)
    validate_target(branch, push_remote)
    if require_clean and command(["git", "status", "--porcelain"]):
        raise CheckError("working tree must be clean")
    command(["gh", "auth", "status", "--hostname", "github.com"])
    try:
        data = json.loads(command([
            "gh", "repo", "view", REPOSITORY, "--json",
            "nameWithOwner,isPrivate,viewerPermission",
        ]))
    except (json.JSONDecodeError, TypeError) as exc:
        raise CheckError("invalid repository metadata") from exc
    if not isinstance(data, dict):
        raise CheckError("invalid repository metadata")
    validate_metadata(data, allow_public)
    return {
        "repository": REPOSITORY,
        "branch": branch,
        "visibility": "private" if data["isPrivate"] else "public",
        "preflight": "PASS",
        "pushed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-public", action="store_true",
                        help="use only after explicit user approval of public push")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.allow_public, args.require_clean), ensure_ascii=False))
        return 0
    except CheckError as exc:
        print(f"preflight: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
