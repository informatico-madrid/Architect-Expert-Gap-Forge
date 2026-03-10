#!/usr/bin/env python3
"""Merge fields into a Ralph state JSON file (atomic write).

Usage:
    python .ralph/scripts/merge_state.py .ralph/state.json --set phase=execution --set taskIndex=0
    python .ralph/scripts/merge_state.py .ralph/state.json --json fixTaskMap='{"T01":{"attempts":1}}'

    # Initialize from tasks.md:
    python .ralph/scripts/merge_state.py .ralph/state.json --init specs/001-feature/tasks.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

TASK_RE = re.compile(r"^- \[(?P<mark>[ xX])\] ")


def count_tasks(tasks_path: Path) -> tuple[int, int, int]:
    """Return (total, completed, next_index) from a tasks.md file."""
    total = 0
    completed = 0
    next_index = None
    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        m = TASK_RE.match(line)
        if not m:
            continue
        if m.group("mark").lower() == "x":
            completed += 1
        elif next_index is None:
            next_index = total
        total += 1
    return total, completed, total if next_index is None else next_index


def parse_scalar(raw: str):
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return int(raw)
    except ValueError:
        return raw


def parse_pairs(items: list[str], as_json: bool) -> dict[str, object]:
    merged: dict[str, object] = {}
    for item in items:
        if "=" not in item:
            print(f"Invalid assignment: {item}", file=sys.stderr)
            raise SystemExit(1)
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            print(f"Empty key in assignment: {item}", file=sys.stderr)
            raise SystemExit(1)
        if as_json:
            try:
                merged[key] = json.loads(value)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON for '{key}': {exc.msg}", file=sys.stderr)
                raise SystemExit(1) from exc
        else:
            merged[key] = parse_scalar(value)
    return merged


def atomic_write(path: Path, data: str) -> None:
    """Write data atomically via temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Ralph state fields into JSON.")
    parser.add_argument("state_file", help="Path to state JSON file")
    parser.add_argument(
        "--set", action="append", default=[], help="key=value scalar assignment"
    )
    parser.add_argument(
        "--json",
        action="append",
        default=[],
        dest="json_pairs",
        help="key=<json> assignment",
    )
    parser.add_argument(
        "--init",
        metavar="TASKS_MD",
        help="Initialize state from tasks.md (reads task counts)",
    )
    parser.add_argument(
        "--stdout", action="store_true", help="Print to stdout instead of writing"
    )
    args = parser.parse_args()

    state_path = Path(args.state_file)
    state: dict = {}

    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(
                f"State file is not valid JSON: {state_path} ({exc.msg})",
                file=sys.stderr,
            )
            return 1
        if not isinstance(state, dict):
            print("State file must contain a JSON object.", file=sys.stderr)
            return 1

    # --init: read tasks.md and populate task fields
    if args.init:
        tasks_path = Path(args.init)
        if not tasks_path.exists():
            print(f"Tasks file not found: {tasks_path}", file=sys.stderr)
            return 1
        total, completed, next_idx = count_tasks(tasks_path)
        state.setdefault("phase", "execution")
        state["taskIndex"] = next_idx
        state["totalTasks"] = total
        state.setdefault("taskIteration", 1)
        state.setdefault("maxTaskIterations", 5)
        state.setdefault("globalIteration", 1)
        state.setdefault("maxGlobalIterations", 100)
        state.setdefault("awaitingApproval", False)
        state.setdefault("recoveryMode", True)
        state.setdefault("maxFixTasksPerOriginal", 3)
        state.setdefault("fixTaskMap", {})

    # Apply overrides
    state.update(parse_pairs(args.set, as_json=False))
    state.update(parse_pairs(args.json_pairs, as_json=True))

    encoded = json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    if args.stdout:
        print(encoded, end="")
        return 0

    atomic_write(state_path, encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
