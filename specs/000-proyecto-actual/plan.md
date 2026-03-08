# Technical Plan — Existing Architecture and Data Flows

This document extracts the implemented technical architecture, module responsibilities, data locations, and interface contracts from the current codebase.

## Architecture Overview

- The repository implements a staged pipeline where each stage is a self-contained module set under `src/`:
  1. Discovery (`src/discovery/`) — ingest source documents and produce normalized artifacts.
  2. Factory (`src/factory/`) — produce synthetic training and eval datasets (checkpoint/resume supported).
  3. Curation (`src/curation/`) — quality filtering and deduplication (NeMo optional).
  4. Training (`configs/stage_4_training/`, training scripts) — trainer config and orchestration.
  5. Audit (`src/audit/`) — evaluation orchestration, prompt manager, inference router.
  6. Merger (`src/merger/`) — consolidation of outputs (present but minimal).

## Key Modules & Responsibilities

- `src/audit/inference.py` — Strategy + Router for inference backends. The router selects `GeminiClient` only when the `google-genai` runtime and `GOOGLE_API_KEY` exist; otherwise `VLLMClient` is used.
- `src/audit/prompt_manager.py` — loads YAML templates from `configs/stage_5_evaluation/` and formats prompt payloads for evaluation.
- `src/audit/model_evaluator.py` — CLI orchestrator for end-to-end evaluations (`sample|baseline|adapter|score|full`). Supports a `--validate` smoke-run mode.
- `src/utils/doc_loader.py` — canonical master-doc loader; fails fast when required documents under `data/Gap/` are missing.
- `src/factory/production_v11.py` — main synthetic generation pipeline with checkpointing and resume logic.

## Internal API Contracts

- Inference client interface (observed pattern):

```python
class BaseInferenceClient(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompt: str, *, system_prompt: str | None = None,
                 max_tokens: int = 4096, temperature: float = 0.7) -> str: ...
```

- `PromptManager` contract: loads templates and returns formatted prompt strings or structured payloads consumable by `BaseInferenceClient` implementations.

## Configuration & Environment

- Important env vars and defaults:
  - `AEGF_VLLM_API_URL` — vLLM endpoint (default `http://localhost:8000/v1`).
  - `GOOGLE_API_KEY` — when present (and `google-genai` installed) triggers Gemini backend selection.
  - `AEGF_DOC_1..3` — used by `doc_loader` to locate master docs in some test flows.
- Prompt templates and pipeline options live in `configs/` per stage.

## Data Storage & Schema (observed)

- Storage is file-backed (no monolithic DB): primary locations are `data/Gap/`, `data/synthetic/`, and `outputs/`.
- Primary exchange format: newline-delimited JSON (JSONL). Typical synthetic records include fields like `id`, `input`/`prompt`, `target`/`completion`, and `metadata` (inferred from generator and tests).

## Data Flow (detailed)

1. **Discovery**: ingestors scan sources, extract text and metadata, and write canonical documents to `data/Gap/`.
2. **Factory**: `production_v11.py` reads master docs + configs and emits synthetic JSONL into `data/synthetic/` (supports partial runs / checkpointing).
3. **Curation (optional)**: curated datasets are produced by `nemo_curator_suite.py` to filter/deduplicate `data/synthetic/` and produce high-quality training sets.
4. **Training**: training consumes curated JSONL according to `configs/stage_4_training/` and trainer tooling (axolotl or equivalent).
5. **Audit**: `model_evaluator.py` loads evaluation prompts from `configs/stage_5_evaluation/`, uses `PromptManager` to build inputs, and calls the inference router to score model outputs against references.
6. **Merger**: final datasets or artifact merges are performed under `src/merger/` (lightweight in current implementation).

## External Dependencies & Runtime Behavior

- The system prefers local emulated/backplane endpoints for CI to avoid calls to remote services. CI uses mocks to satisfy behavior.
- Router selects backend at runtime; clients must adhere to the `BaseInferenceClient` contract.

## Observed Operational Constraints

- Several folders under `src/` lack `__init__.py`; when packaging or importing, prefer `python -m` patterns or add `__init__.py` where necessary.
- Header and commit conventions are enforced by repository tooling — new Python sources must include the project's header and pass `scripts/check_headers.py`.

## Maintenance & Immediate Next Steps (low-effort)

- Add missing `__init__.py` for packages that must be importable under standard `import` semantics, or standardize on `python -m` runs.
- Add a small schema document for the JSONL record structure (fields and types) to reduce ambiguity between stages.

---
This plan reflects the code that is present now and documents the implemented contracts and flow used by current scripts and tests.
