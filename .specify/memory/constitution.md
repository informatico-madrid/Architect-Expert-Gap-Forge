# Project Constitution — Architectural & Coding Rules (AEGF)

This document records the conventions, architectural patterns, toolchain and governance that are actively enforced by the repository at the time of extraction. It is derived from in-repo artefacts (notably `AGENTS.md`, `.github/copilot-instructions.md`, `src/` modules and `configs/`). Use this as the canonical, machine-readable summary of "how we work".

## Purpose

- Capture the project's implicit and explicit rules so tooling and contributors can be consistent.
- Describe the required developer & CI checks that must run before code is staged or merged.

## Technology Stack (observed)

- **Language:** Python 3.12+
- **Core libs:** PyYAML, pydantic, requests, python-dotenv, tqdm
- **Optional/infra:** google-genai (Gemini SDK), vLLM backend (AEGF_VLLM_API_URL), NeMo components (optional imports)
- **QA & formatting:** pytest, pytest-cov, ruff (formatter), pyright (type checking in CI)

## High-level Architecture & Pipeline

- Pipeline stages (implemented): Discovery → Factory → Curation → Training → Quality Gate (Audit) → Merger.
- Stage code locations under `src/`:
  - `src/discovery/` — ingestion & processor
  - `src/factory/` — synthetic data generation (e.g. `production_v11.py`)
  - `src/curation/` — optional NeMo-based curation
  - `src/audit/` — evaluation pipeline, inference router, prompt manager
  - `src/utils/` — shared helpers (e.g. `doc_loader.py`)

## Coding Conventions (enforced / expected)

- **Strict typing:** all public functions and methods must be fully annotated. Use `TypedDict`, `@dataclass(slots=True, frozen=True)` and `pydantic` models for structured data.
- **Immutability by default:** data records should be frozen dataclasses or immutable models unless there is an explicit lifecycle reason to mutate.
- **No import-time side-effects:** module import must not trigger I/O, network calls, or client instantiation.
- **Logging:** one logger per module `logger = logging.getLogger(__name__)`. Use lazy formatting: `logger.info("Loaded %d records", n)` (no f-strings in logger calls).
- **Concurrency:** async code uses structured concurrency (`asyncio.TaskGroup`) when appropriate; wrap blocking I/O in `asyncio.to_thread()`.
- **Error handling:** explicit exceptions only; no bare `except: pass`. Do not use `SystemExit` for flow-control.

## Patterns & Design Constraints

- **Strategy + Router:** inference backends are behind a strategy interface and selected by a router (see `src/audit/inference.py`).
- **Prompt externalization:** all prompt templates live under `configs/` and are formatted by `PromptManager` (`src/audit/prompt_manager.py`).
- **Plural / batch operations favored:** batch generation and persistence rather than record-by-record operations.
- **SRP & module size:** modules should be small and single-responsibility; prefer extraction to `src/utils/` for cross-cutting concerns.

## Testing & Coverage

- Unit tests and integration tests are required for new modules. Use `pytest` and typed fixtures in `tests/`.
- Coverage requirements: CI expects >= 90% coverage for tracked modules (`src/audit`, `src/utils`), enforced by `make coverage` settings.
- Avoid `# pragma: no cover` except for unavoidable boilerplate and document any exception.

## Repository & CI Governance

- **No remote history changes:** agents and automation must not run `git commit`/`git push` without human confirmation.
- **Staging policy:** files may be created/edited, but staging/committing requires explicit human approval.
- **Header policy for new source files:** Python source files must include the project header (shebang, project id `Architect-Expert-Gap-Forge (AEGF)`, copyright, SPDX license); CI checks headers with `scripts/check_headers.py --check`.
- **Commit message style:** Conventional Commits required for proposed commit messages (type(scope?): subject).

## Data & Prompts

- Master documents (single source truth) live under `data/Gap/` and are required by `src/utils/doc_loader.py` (the loader raises if missing).
- Prompt templates are stored under `configs/stage_*` (notably `stage_5_evaluation`) and loaded by `PromptManager`.
- Default data exchange format is JSONL for datasets and synthetic outputs (`data/synthetic/`, `outputs/`).

## External Integrations & Backends

- **vLLM**: default inference endpoint configured via `AEGF_VLLM_API_URL` (default `http://localhost:8000/v1`).
- **Gemini (google-genai)**: chosen only when the `google-genai` package is present *and* `GOOGLE_API_KEY` is set.
- **NeMo Curator & NeMo Guardrails:** optional integrations guarded by try/except; do not break core flows when absent.

## Security & Secrets

- Never store credentials in source. Use environment variables and `.example` files for config templates.
- CI uses local mocks for external services; avoid live external calls during CI.

## Agent / Automation Rules (observed)

- Agents must announce planned edits via the repository todo process and wait for human confirmation before staging files.
- Automation must not alter remote repository history. `git commit` and `git push` are forbidden without explicit human approval.

## Non-negotiables (observed constraints)

- DRY: duplicate logic must be extracted to shared modules.
- No silent failures: parse or validation errors must raise explicit exceptions.

---
This constitution is an extraction of the current repo state and should be updated when the codebase rules evolve. For authoritative source-of-truth see `AGENTS.md` and `.github/copilot-instructions.md` in the repository root.
