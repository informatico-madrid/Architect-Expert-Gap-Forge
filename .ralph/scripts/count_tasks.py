#!/usr/bin/env python3
"""Parse tasks.md and output structured JSON with task status, phases, and next task.

Usage:
    python .ralph/scripts/count_tasks.py specs/001-stage1-discovery/tasks.md
    python .ralph/scripts/count_tasks.py specs/001-stage1-discovery/tasks.md --full

Output (default):
    {"total": 32, "completed": 10, "incomplete": 22, "next_index": 10, "percent": 31}

Output (--full):  includes per-task detail array
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TASK_LINE_RE = re.compile(
    r"^- \[(?P<mark>[ xX])\]\s+"
    r"(?P<id>[TV]\d+)?\s*"
    r"(?P<tags>(?:\[[^\]]+\]\s*)*)"
    r"(?P<desc>.*)"
)

PHASE_RE = re.compile(r"^##?\s+(?:Phase\s+\d+|Final Phase|Additional)", re.IGNORECASE)
VERIFY_TAG = re.compile(r"\[VERIFY\]", re.IGNORECASE)
PARALLEL_TAG = re.compile(r"\[P\]")
USERSTORY_TAG = re.compile(r"\[US(\d+)\]")
DEPENDS_RE = re.compile(r"\(depends on (\w+)\)")


def parse_tasks(tasks_path: Path, full: bool = False) -> dict:
    text = tasks_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    tasks: list[dict] = []
    current_phase = "Unknown"
    total = 0
    completed = 0
    next_index: int | None = None

    for line in lines:
        phase_match = PHASE_RE.match(line)
        if phase_match:
            current_phase = line.lstrip("#").strip()
            continue

        m = TASK_LINE_RE.match(line)
        if not m:
            continue

        is_done = m.group("mark").lower() == "x"
        task_id = m.group("id") or f"T{total + 1:03d}"
        tags_str = m.group("tags").strip()
        desc = m.group("desc").strip()

        is_verify = bool(VERIFY_TAG.search(tags_str + " " + desc))
        is_parallel = bool(PARALLEL_TAG.search(tags_str))
        us_match = USERSTORY_TAG.search(tags_str)
        user_story = f"US{us_match.group(1)}" if us_match else None
        dep_match = DEPENDS_RE.search(desc)
        depends_on = dep_match.group(1) if dep_match else None

        if is_done:
            completed += 1
        elif next_index is None:
            next_index = total

        if full:
            tasks.append(
                {
                    "index": total,
                    "id": task_id,
                    "done": is_done,
                    "phase": current_phase,
                    "parallel": is_parallel,
                    "verify": is_verify,
                    "userStory": user_story,
                    "dependsOn": depends_on,
                    "description": desc,
                }
            )

        total += 1

    payload: dict = {
        "total": total,
        "completed": completed,
        "incomplete": total - completed,
        "next_index": total if next_index is None else next_index,
        "percent": round(completed / total * 100) if total > 0 else 0,
    }

    if full:
        payload["tasks"] = tasks

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count and parse Ralph task checkboxes."
    )
    parser.add_argument("tasks_file", help="Path to tasks.md")
    parser.add_argument(
        "--full", action="store_true", help="Include per-task detail array"
    )
    args = parser.parse_args()

    task_path = Path(args.tasks_file)
    if not task_path.exists():
        print(
            json.dumps({"error": f"Tasks file not found: {task_path}"}), file=sys.stderr
        )
        return 1

    result = parse_tasks(task_path, full=args.full)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
