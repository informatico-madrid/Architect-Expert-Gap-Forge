# AEGF: Project Operations (AGENTS.md) — Synchronized

This file documents the project's operational surface and the expected governance constraints. It has been synchronized against the repository state (scanned on 2026-03-04).

**Project Root:** `/mnt/bunker_data/ai/data_factory`

## 🛠 Operational Stack
- **Language:** Python 3.12+ project uses modern typing; strict typing
- **Inference:** vLLM (OpenAI-compatible HTTP endpoint) + optional Google GenAI SDK. See `src/audit/inference.py` for the `GeminiClient` / `VLLMClient` router.
- **Curation:** `nemo_curator` integration (guarded by import checks in `src/curation/nemo_curator_suite.py`).
- **Training:** Axolotl are documented in the repository skills and docs
- **Formatting / QA:** `ruff` is the active formatter referenced by `Makefile` (`make fmt`).
- **Environment:** Linux (Bunker); CI targets `ubuntu-latest` in GitHub Actions.

## 📂 Project Anatomy (discovered)
- `src/audit/` — present; includes `__init__.py` and core evaluation code (`inference.py`, `model_evaluator.py`, `prompt_manager.py`, `schema.py`, `persistence.py`, `sampling.py`).
- `src/utils/` — present and package-initialised (`__init__.py`), contains `doc_loader.py` and helpers.
- `src/discovery/` — contains `ingestor.py`, `processor.py` **but lacks** `__init__.py` (not a package currently).
- `src/factory/` — contains `production_v11.py`, `agentic_gen.py`, `think_filter.py` **but lacks** `__init__.py`.
- `src/curation/` — contains `nemo_curator_suite.py` **but lacks** `__init__.py`.
- `src/merger/` — exists but currently empty (no implementation files).
- `src/research/` — present and initialised (`__init__.py`), experimental scripts under `src/research/`.
- `configs/` — present with `stage_1_discovery/` to `stage_5_evaluation/` and taxonomies.
- `tests/` — present (pytest-based test suite).

## 📦 Dependencies (declared)
- Runtime (from `pyproject.toml` / `requirements.txt`): `PyYAML`, `pydantic`, `requests`, `google-genai` (optional), `python-dotenv`, `tqdm`.
- Dev: `pytest`, `pytest-cov` (declared in `requirements-dev.txt`).
- Notes: `nemo_curator`, `datasketch` are used behind optional imports (try/except) in `src/curation/nemo_curator_suite.py` and are not required for unit tests unless you exercise the NeMo path.

## 🧰 Tooling & CI
- Tests / coverage: `make test` / `make coverage` — coverage configured in `pyproject.toml` and `Makefile` (tracked sources: `src/audit`, `src/utils`; `--cov-fail-under=90`).
- Formatting: `make fmt` runs `ruff format` (install `ruff` in dev environment).
- Lint/type-check: `make lint` runs `pyright` (optional).

## 📜 Governance Reference
All code should conform to the **Architectural Gold Standard** defined in `.github/agents/AEGF.agent.md`. This document remains the canonical policy;

---