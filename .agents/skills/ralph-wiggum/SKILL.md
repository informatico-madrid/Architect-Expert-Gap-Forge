---
name: ralph-wiggum
description: "Autonomous AI coding with spec-driven development. Implements Geoffrey Huntley's iterative bash loop with SpecKit integration: JSON state machine, three-layer verification, [VERIFY] checkpoints, recovery mode, and structured task format (Do/Files/Done-when/Verify/Commit)."
license: MIT
metadata:
  author: fstandhartinger
  version: "2.0"
  repository: https://github.com/fstandhartinger/ralph-wiggum
  website: https://ralph-wiggum.ai
---

# Ralph Wiggum — SpecKit Integrated Edition

> Autonomous AI coding with spec-driven development + multi-layer verification

## What is Ralph Wiggum?

Ralph Wiggum combines **Geoffrey Huntley's iterative bash loop** with **spec-driven development** and **structured verification** for fully autonomous AI-assisted software development.

Key insight: **Fresh context each iteration** + **JSON state machine** + **three-layer verification** prevents false-positive completions.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   RALPH LOOP (SpecKit Edition)                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────────────────┐ │
│  │  State   │───▶│  WORK PHASE  │───▶│  VERIFICATION (3 layers)│ │
│  │  .json   │    │  (Agent)     │    │  1. Contradiction check │ │
│  │          │    │              │    │  2. Signal verify       │ │
│  │taskIndex │    │  Executes    │    │  3. Artifact review     │ │
│  │iteration │    │  ONE task    │    │     (every N tasks)     │ │
│  │retries   │    │              │    │                         │ │
│  └────▲─────┘    └──────────────┘    └────────────┬────────────┘ │
│       │                                           │              │
│       │              ┌───────────┐                │              │
│       └──────────────│  UPDATE   │◀───────────────┘              │
│                      │  STATE    │                               │
│                      │ tasks.md  │                               │
│                      │ progress  │                               │
│                      └───────────┘                               │
│                                                                  │
│  Signals: TASK_COMPLETE | ALL_TASKS_COMPLETE                     │
│  Recovery: auto-generate fix tasks (up to 3 per failed task)     │
│  Safety: per-task retry limit + global iteration cap             │
└──────────────────────────────────────────────────────────────────┘
```

## When to Use

- You have specs with structured tasks (tasks.md)
- You want autonomous implementation with verified completion
- You need to prevent false positives (tasks marked done when they aren't)
- You want state persistence across interrupted sessions (--resume)

## File Structure

```
.ralph/
├── ralph-loop.sh              # Main loop script
├── state.json                 # JSON state machine (auto-managed)
├── review-feedback.txt        # Feedback from last review (ephemeral)
├── schemas/
│   └── ralph-state.schema.json
├── scripts/
│   ├── count_tasks.py         # Parse tasks.md → JSON counts
│   └── merge_state.py         # Atomic state updates
└── recipes/                   # Goose recipes (if using goose)
    ├── ralph-work.yaml
    └── ralph-review.yaml
```

## Task Format (REQUIRED)

Every task in `tasks.md` must have this structure:

```markdown
- [ ] T010 [P] [US1] Task description
  - **Do**: 1. Step one 2. Step two 3. Step three
  - **Files**: src/module.py, tests/test_module.py
  - **Done when**: Test file exists and pytest discovers it
  - **Verify**: `pytest tests/test_module.py -v`
  - **Commit**: `feat(scope): description`
```

### Tags
- `[P]` = parallel execution allowed
- `[US#]` = user story tracking
- `[VERIFY]` = quality checkpoint (delegated to QA review)
- `(depends on T###)` = dependency

### Quality Checkpoints
Insert `[VERIFY]` tasks every 2-3 phases:

```markdown
- [ ] V001 [VERIFY] Quality gate: pytest tests/ && ruff check src/
  - **Verify**: `pytest tests/ -x --tb=short && ruff check src/`
  - **Done when**: All checks pass (exit 0)
```

## Three-Layer Verification

### Layer 1: Contradiction Detection
If agent says "requires manual" or "cannot complete" BUT also claims TASK_COMPLETE → **REJECT**.

### Layer 2: Signal Verification
Agent MUST output `TASK_COMPLETE` or `ALL_TASKS_COMPLETE`. No signal = retry.

### Layer 3: Artifact Review (Periodic)
Every N tasks (configurable), run a reviewer agent to check:
- Code matches plan.md architecture
- Constitution rules followed
- Tests and lint pass
- No hallucinated dependencies

## State Machine (.ralph/state.json)

```json
{
  "featureId": "001",
  "name": "stage1-discovery",
  "basePath": "specs/001-stage1-discovery",
  "phase": "execution",
  "taskIndex": 9,
  "totalTasks": 36,
  "taskIteration": 1,
  "maxTaskIterations": 5,
  "globalIteration": 1,
  "maxGlobalIterations": 100,
  "recoveryMode": true,
  "fixTaskMap": {}
}
```

## Usage

```bash
# Execute a spec
.ralph/ralph-loop.sh specs/001-stage1-discovery

# With options
.ralph/ralph-loop.sh specs/001-feature --max 50 --review-every 3

# Resume interrupted session
.ralph/ralph-loop.sh --resume

# Use goose instead of claude
RALPH_AGENT=goose .ralph/ralph-loop.sh specs/001-feature
```

## Completion Signals

| Signal | Meaning |
|--------|---------|
| `TASK_COMPLETE` | Current task verified and done |
| `ALL_TASKS_COMPLETE` | All tasks in tasks.md are [x] |
| (no signal) | Task not complete, will retry |

## Integration with SpecKit Agents

The Ralph Loop works with the speckit agent chain:

1. `speckit.specify` → Creates spec.md
2. `speckit.plan` → Creates plan.md
3. `speckit.tasks` → Creates tasks.md (with Do/Files/Done-when/Verify/Commit)
4. **Ralph Loop** → Executes tasks.md autonomously

## Links

- **Original methodology:** [Geoffrey Huntley's how-to-ralph-wiggum](https://github.com/ghuntley/how-to-ralph-wiggum)
- **Smart Ralph plugin:** [tzachbon/smart-ralph](https://github.com/tzachbon/smart-ralph)
- **Ralph SpecKit standalone:** [merllinsbeard/ralph-speckit](https://github.com/merllinsbeard/ralph-speckit)
