# Architect-Expert-Gap-Forge (AEGF) Constitution

> AEGF is a high-performance pipeline designed to solve the **Knowledge Cutoff problem** in Large Language Models. While frontier models are excellent generalists, they often hallucinate or fail when dealing with rapidly evolving APIs, legacy-to-modern migrations, or domain-specific architectures (e.g., Home Assistant 2026 standards).

## Version
1.0.0

## 🔍 Context Detection

### Context A: Ralph Loop (Implementation Mode)

You are in a Ralph loop if:
- Started by `ralph-loop.sh`
- Prompt mentions "implement spec"
- A `.ralph/state.json` exists and is active

**In this mode:**
- Focus on implementation of the CURRENT task (from tasks.md)
- Complete ALL acceptance criteria in the task's **Done when** field
- Run the **Verify** command to confirm completion
- Mark the task as `[x]` in tasks.md
- Append progress to `progress.txt`
- Output `TASK_COMPLETE` when current task is verified
- Output `ALL_TASKS_COMPLETE` when all tasks in tasks.md are done
- NEVER output completion signals unless the task genuinely passes verification

### Context B: Interactive Chat

When not in a Ralph loop:
- Be helpful and conversational
- Create specs with `/speckit.specify`

---

## Core Principles

### I. Purpose
- Capture the project's implicit and explicit rules so tooling and contributors can be consistent.
- Describe the required developer & CI checks that must run before code is staged or merged.

### II. Testing & Coverage

- Unit tests and integration tests are required for new modules. Use `pytest` and typed fixtures in `tests/`.
- Coverage requirements: CI expects >= 90% coverage for tracked modules (`src/audit`, `src/utils`), enforced by `make coverage` settings.
- Avoid `# pragma: no cover` except for unavoidable boilerplate and document any exception.

### III. Coding Conventions (enforced / expected)

- **Strict typing:** all public functions and methods must be fully annotated. Use `TypedDict`, `@dataclass(slots=True, frozen=True)` and `pydantic` models for structured data.
- **Immutability by default:** data records should be frozen dataclasses or immutable models unless there is an explicit lifecycle reason to mutate.
- **No import-time side-effects:** module import must not trigger I/O, network calls, or client instantiation.
- **Logging:** one logger per module `logger = logging.getLogger(__name__)`. Use lazy formatting: `logger.info("Loaded %d records", n)` (no f-strings in logger calls).
- **Concurrency:** async code uses structured concurrency (`asyncio.TaskGroup`) when appropriate; wrap blocking I/O in `asyncio.to_thread()`.
- **Error handling:** explicit exceptions only; no bare `except: pass`. Do not use `SystemExit` for flow-control.

### IV. Patterns & Design Constraints

- **Strategy + Router:** inference backends are behind a strategy interface and selected by a router (see `src/audit/inference.py`).
- **Prompt externalization:** all prompt templates live under `configs/` and are formatted by `PromptManager` (`src/audit/prompt_manager.py`).
- **Plural / batch operations favored:** batch generation and persistence rather than record-by-record operations.
- **SRP & module size:** modules should be small and single-responsibility; prefer extraction to `src/utils/` for cross-cutting concerns.

### V. Repository & CI Governance

- **Header policy for new source files:** Python source files must include the project header (shebang, project id `Architect-Expert-Gap-Forge (AEGF)`, copyright, SPDX license); CI checks headers with `scripts/check_headers.py --check`.

### VI Security & Secrets

- Never store credentials in source. Use environment variables and `.example` files for config templates.
- CI uses local mocks for external services; avoid live external calls during CI.

### VII Non-negotiables (observed constraints)

- DRY: duplicate logic must be extracted to shared modules.
- No silent failures: parse or validation errors must raise explicit exceptions.

### VIII. Simplicity & YAGNI
Build exactly what's needed, nothing more.

---

## Autonomy Configuration

### YOLO Mode: [ENABLED]
### Git Autonomy: [ENABLED]

---



# Project Constitution — Architectural & Coding Rules (AEGF)

This document records the conventions, architectural patterns, toolchain and governance that are actively enforced by the repository at the time of extraction. It is derived from in-repo artefacts (notably `AGENTS.md`, `.github/copilot-instructions.md`, `src/` modules and `configs/`). Use this as the canonical, machine-readable summary of "how we work".
