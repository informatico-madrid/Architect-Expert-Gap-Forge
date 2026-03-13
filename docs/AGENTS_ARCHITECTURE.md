# Project Agents Architecture

> This document provides an overview of the orchestration system to understand how the autonomous development pipeline works. For agent context files, see `.github/agents/` and `.specify/memory/`.

---

## 🎯 System Overview

The AEGF orchestration system consists of two complementary layers:

1. **Speckit Protocol** — The Requirement Validation Layer
2. **Ralph Loop** — The Autonomous Execution Layer

---

## 🔧 Speckit Protocol: Requirement Validation Layer

### What is Speckit?

Speckit is **not a folder of scripts** — it is the **Requirement Validation Protocol** that guarantees every line of code has a prior technical justification. It serves as the **SDD Enforcer** (Spec-Driven Development).

### The Protocol Guarantees

| Guarantee | Description |
|-----------|-------------|
| **Traceability** | Every code change maps to a specification |
| **Verification** | Each task has explicit acceptance criteria |
| **Compliance** | No code lands without passing the verification checkpoint |
| **Auditability** | All decisions are recorded in `tasks.md` with `[x]` completion markers |

### Speckit Workflow

```
/specify (What) → /clarify (Ambiguities) → /analyze (Context) → /plan (How)
     → /tasks (Breakdown) → /implement (Code) → /checklist (Verify) → /qa (Validate)
```

### Speckit Agents

Each agent in the workflow enforces a specific validation gate:

| Agent | Validation Gate |
|-------|-----------------|
| `speckit.specify` | Defines what will be built |
| `speckit.clarify` | Resolves ambiguous requirements |
| `speckit.analyze` | Analyzes existing code and dependencies |
| `speckit.plan` | Creates technical implementation plan |
| `speckit.tasks` | Generates executable task checklist |
| `speckit.implement` | Executes implementation |
| `speckit.checklist` | Verifies acceptance criteria |
| `speckit.qa` | Runs quality assurance tests |
| `speckit.constitution` | Enforces project rules |
| `speckit.taskstoissues` | Converts tasks to GitHub issues |

---

## ⚙️ Ralph Loop: Autonomous Execution Layer

### What is Ralph Loop?

Ralph Loop is the autonomous coding engine that executes tasks from the Speckit checklist without human intervention between tasks. It operates **statelessly** — each iteration is independent and context-cleared.

### Parallelization: Factory Pipeline

Factory pipeline implements **parallel execution via async task scheduling**. This allows the system to:

- Execute multiple tasks concurrently using async scheduling
- Manage task dependencies and ordering automatically
- Scale horizontally across available resources
- Progress on multiple features simultaneously

The async task scheduler coordinates parallel execution without requiring isolated working directories.

### Ralph Loop Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Stateless** | Clears context after each task to prevent token accumulation |
| **Checkpointed** | Uses `state.json` to track progress |
| **Verifiable** | Requires explicit task completion signals |
| **Recoverable** | Supports `--resume` for failure recovery |
| **Parallel** | Uses async task scheduling for concurrent spec execution |

### The Loop Flow

```
1. Find next incomplete task in tasks.md
2. Implement the task
3. Run verification tests
4. Mark task as [x] in tasks.md
5. Commit changes
6. Output TASK_COMPLETE
7. Clear context and repeat
```

---

## 🏛️ Definitions Location

| Type | Path |
|------|------|
| Agent Definitions | `.github/agents/*.agent.md` |
| Speckit Prompts | `.github/prompts/speckit.*.prompt.md` |
| Project Constitution | `.specify/memory/constitution.md` |
| Workflow Stack | `.specify/memory/workflow-stack.md` |

---
