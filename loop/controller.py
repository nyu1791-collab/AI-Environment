"""Bounded agent loop controller.

The controller owns state, limits, retries and verification. The worker
(an agent command) is a short-lived process that does one bounded unit of work.

Task contract (JSON):
  {
    "goal": "text",
    "worker": ["cmd", "arg", ...],     # run in workdir
    "checks": [["cmd", "arg", ...]],   # each must exit 0 for the iteration to pass
    "allowed_paths": ["src/", "tests/"],  # worker may change only these (checked by git-free snapshot)
    "max_iterations": 5,
    "retry_budget": 3,                 # consecutive failures before halting for a human
    "time_limit_sec": 3600
  }

State is kept in <state_dir>/state.json and appended log in <state_dir>/log.md.
Re-running the controller resumes from state.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

REQUIRED = ("goal", "worker", "checks", "max_iterations", "retry_budget", "time_limit_sec")


@dataclass
class State:
    iteration: int = 0
    consecutive_failures: int = 0
    status: str = "pending"  # pending | running | passed | halted_budget | halted_limit | halted_time
    started_at: float = field(default_factory=time.time)
    history: list = field(default_factory=list)


def load_contract(path: Path) -> dict:
    contract = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in contract]
    if missing:
        raise ValueError(f"contract missing keys: {missing}")
    if contract["max_iterations"] < 1 or contract["retry_budget"] < 1:
        raise ValueError("max_iterations and retry_budget must be >= 1")
    if not contract["worker"] or not all(contract["checks"]):
        raise ValueError("worker and each check must be non-empty commands")
    return contract


def load_state(state_dir: Path) -> State:
    path = state_dir / "state.json"
    if path.exists():
        return State(**json.loads(path.read_text(encoding="utf-8")))
    return State()


def save_state(state_dir: Path, state: State) -> None:
    # Write to a temp file then rename, so a crash never leaves a half-written state.
    tmp = state_dir / "state.json.tmp"
    tmp.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, state_dir / "state.json")


def append_log(state_dir: Path, line: str) -> None:
    with (state_dir / "log.md").open("a", encoding="utf-8") as f:
        f.write(f"- {time.strftime('%Y-%m-%dT%H:%M:%S%z')} {line}\n")


def run_cmd(cmd: list[str], cwd: Path, timeout: float) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout + proc.stderr)[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except FileNotFoundError as exc:
        return 127, f"command not found: {exc}"


def out_of_bounds(before: dict[str, float], after: dict[str, float], allowed: list[str]) -> list[str]:
    """Return changed paths outside allowed_paths. Snapshot = {path: mtime}."""
    changed = [p for p in set(before) | set(after) if before.get(p) != after.get(p)]
    return sorted(p for p in changed if not any(p.startswith(a) for a in allowed))


def snapshot(workdir: Path) -> dict[str, float]:
    snap: dict[str, float] = {}
    for root, dirs, files in os.walk(workdir):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "logs")]
        for name in files:
            p = Path(root) / name
            snap[str(p.relative_to(workdir))] = p.stat().st_mtime
    return snap


def run(contract_path: Path, workdir: Path, state_dir: Path) -> State:
    contract = load_contract(contract_path)
    state_dir.mkdir(parents=True, exist_ok=True)
    state = load_state(state_dir)
    if state.status in ("passed", "halted_budget", "halted_limit", "halted_time"):
        append_log(state_dir, f"already finished: {state.status}")
        return state
    state.status = "running"
    allowed = contract.get("allowed_paths", [])
    deadline = state.started_at + contract["time_limit_sec"]

    while state.iteration < contract["max_iterations"]:
        if time.time() > deadline:
            state.status = "halted_time"
            break
        state.iteration += 1
        before = snapshot(workdir)
        rc, out = run_cmd(contract["worker"], workdir, timeout=max(1.0, deadline - time.time()))
        after = snapshot(workdir)
        violations = out_of_bounds(before, after, allowed) if allowed else []

        checks_ok = rc == 0 and not violations
        if checks_ok:
            for check in contract["checks"]:
                c_rc, c_out = run_cmd(check, workdir, timeout=max(1.0, deadline - time.time()))
                if c_rc != 0:
                    checks_ok = False
                    out = f"check {check} failed rc={c_rc}: {c_out}"
                    break

        state.history.append({"iteration": state.iteration, "worker_rc": rc, "violations": violations, "passed": checks_ok})
        if checks_ok:
            state.consecutive_failures = 0
            state.status = "passed"
            append_log(state_dir, f"iteration {state.iteration} passed")
            save_state(state_dir, state)
            return state

        state.consecutive_failures += 1
        reason = f"violations={violations}" if violations else f"worker_rc={rc}"
        append_log(state_dir, f"iteration {state.iteration} failed ({reason}); output: {out[-300:]!r}")
        save_state(state_dir, state)
        if state.consecutive_failures >= contract["retry_budget"]:
            state.status = "halted_budget"
            break

    if state.status == "running":
        state.status = "halted_limit"
    append_log(state_dir, f"stopped: {state.status}")
    save_state(state_dir, state)
    return state


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("contract", type=Path)
    p.add_argument("--workdir", type=Path, required=True)
    p.add_argument("--state-dir", type=Path, required=True)
    a = p.parse_args()
    result = run(a.contract, a.workdir, a.state_dir)
    print(result.status)
    raise SystemExit(0 if result.status == "passed" else 1)
