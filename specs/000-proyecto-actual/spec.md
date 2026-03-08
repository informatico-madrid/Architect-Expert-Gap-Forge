# Functional Specification — Current Implementation

This document describes the functionality that the repository currently implements, the primary use-cases it serves, and the business rules encoded in the codebase.

## Overview

- The project implements a multi-stage data & model pipeline: Discovery → Factory → Curation → Training → Audit (Quality Gate) → Merger.
- Functionality is organized into `src/` modules and externalized configuration in `configs/` and `data/`.

## Implemented Features

- **Discovery**
  - Repository ingestion and metadata extraction are implemented under `src/discovery/` (`ingestor.py`, `processor.py`). These modules collect and normalize source documents used later in generation.

- **Factory (Synthetic Data Generation)**
  - `src/factory/production_v11.py` is the main generation pipeline that produces synthetic datasets for training. It supports checkpointing and resume.
  - Multi-turn, agentic generation utilities live in `src/factory/agentic_gen.py`.
  - Chain-of-thought distillation and filtering utilities in `src/factory/think_filter.py`.
  - A generator example is documented in repository notes (see `production_v11.py` sample CLI usage).

- **Curation**
  - `src/curation/nemo_curator_suite.py` orchestrates optional NeMo-based quality filtering and deduplication; the module is guarded so the core flows work even when NeMo is not installed.

- **Training**
  - Training orchestration is supported via configuration under `configs/stage_4_training/` and helper scripts, using axolotl/other trainer stacks as configured.

- **Audit / Evaluation**
  - `src/audit/model_evaluator.py` is a CLI orchestrator exposing commands: `sample | baseline | adapter | score | full`. It integrates with `PromptManager` and an inference `Router` to run evaluations.
  - `src/audit/prompt_manager.py` loads prompt templates from `configs/stage_5_evaluation/` and formats evaluation prompts.
  - `src/audit/inference.py` implements a Strategy + Router pattern to pick between backends (`vLLMClient`, `GeminiClient`) depending on environment and installed SDKs.

- **Utilities**
  - `src/utils/doc_loader.py` implements master-doc resolution and raises if required master docs (data/Gap/*) are missing.

## Data & Formats

- Primary dataset format: JSONL for synthetic datasets and evaluation outputs (`data/synthetic/`, `outputs/`).
- Prompts and config: YAML under `configs/` (externalized templates for all prompt text).
- Master documents: located in `data/Gap/` and treated as the canonical context for generation and evaluation.

## CLI and Examples

- Evaluator smoke/validate command (example):

```
python -m src.audit.model_evaluator full \
  --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \
  --base-model qwen3-30b-a3b-thinking-fp8 --adapter-model platinum_adapter --validate
```

- Generator example (repository note):

```
python src/factory/production_v11.py --gap-dir data/Gap --test 10
```

## Business Rules & Operational Constraints

- **Prompt externalization:** all prompt text must live in `configs/` and be loaded via `PromptManager`.
- **Master docs required:** `doc_loader` enforces `data/Gap/` presence; runs fail if masters are missing.
- **No external calls in CI:** tests and CI use local mocks; avoid live API calls during CI runs.
- **Coverage enforcement:** coverage thresholds are enforced for `src/audit` and `src/utils` (>= 90%).

## Use Cases Supported

- Produce high-quality synthetic datasets for SFT and fine-tuning.
- Run structured model evaluations using prompt templates and multiple backends.
- Curate and filter large raw corpora using optional GPU-accelerated tooling.

## Limitations & Observed Constraints

- Several `src/` subfolders (e.g., `src/discovery`, `src/factory`, `src/curation`) lack `__init__.py` and behave differently under `importlib` vs `python -m` execution modes.
- External integrations are optional; absence of optional packages should not break core flows.

---
This specification strictly documents the behavior implemented in repository code as found in the working tree. It is not a roadmap — it describes present capabilities and constraints.
