# Feature Specification: Project Maintenance

**Feature Branch**: `006-project-maintenance`  
**Created**: 2026-03-18  
**Status**: Draft  
**Input**: User description: "Project maintenance: fix merger folder, formatting, backend defaults, and experimental pipeline"
---

## 📋 Evaluación de Puntos del TODO.md

Esta especificación consolida los puntos del TODO.md tras evaluación exhaustiva del código base actual:

### ✅ Puntos YA IMPLEMENTADOS (excluidos de esta spec)

1. **Monolith modules** - ✅ Completado en spec 003
   - `src/factory/production_v11.py` eliminado → reemplazado por módulos pequeños (<400 LOC)
   - `src/audit/model_evaluator.py` eliminado → reemplazado por módulos pequeños (<400 LOC)
   - Módulos actuales: `agentic_cli.py`, `agentic_prompt_builder.py`, `checkpoint.py`, `cli.py`, etc.

2. **Secrets & CI behaviour** - ✅ Ya está bien implementado
   - `GOOGLE_API_KEY` controla uso de Gemini
   - CI deja `GOOGLE_API_KEY` vacío y usa vLLM
   - No requiere cambios

3. **Refactor tests** - ✅ Estructura completa existe
   - Tests bien organizados en `tests/` con fixtures, integration, unit
   - Cobertura objetivo 90%+ para módulos principales
   - No requiere cambios en esta spec

### ❌ Puntos que REQUIEREN ACCIÓN (incluidos en esta spec)

2. **src/merger/** - ❌ No existe, scripts dispersos en `data/weights/stage1_pure/` y `data/weights/stage2_final_consolidated/`
   - Scripts de merge stage1: `check_alignment.py`, `clean_dna.py`, `dna_fix_v2.py`, `dna_strict.py`, `final_ignition.py`, `merge_shards.py`, `repair_dna.py`, `repair_triple_dna.py`, `shotgun_dna.py`
   - Scripts de merge stage2: `analisis_avanzado.py`, `diagnostico.py`, `fusionar_final.py`, `repara_stage2.py`, `guardar_tokenizador.py`
   - **Acción**: Crear `src/merger/` y mover TODOS los scripts Python (.py) de ambas ubicaciones (14 scripts total)

3. **Formatting** - ⚠️ Makefile usa ruff ✅, pero `requirements-dev.txt` NO tiene ruff ❌
   - **Acción**: Agregar `ruff>=0.9` a `requirements-dev.txt`

4. **Default backend** - ❌ Sigue en `"auto"` que selecciona gemini si hay clave
   - `src/audit/config.py:140`: `DEFAULT_PROFESSOR_BACKEND = "auto"`
   - `configs/stage_5_evaluation/eval_config.yaml:21`: `professor_backend: "auto"`
   - **Acción**: Cambiar a `"vllm"` por defecto

5. **Pruebas rápidas** - ❌ 0/5 archivos existen
   - **Acción**: Crear `src/research/train_tokenizer.py`, `src/audit/eval_bpb.py`, `src/research/experiment_orchestrator.py`, `docs/experiments.md`, `configs/stage_4_training/axolotl/README.md`
## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish Canonical Development Tooling (Priority: P1)

As a developer, I want the project to have a clearly defined and consistently enforced formatting tool so that I can focus on writing code rather than debating style conventions.

**Why this priority**: Establishing canonical tooling is foundational - without it, every PR introduces style debates and the CI cannot reliably enforce code quality.

**Independent Test**: Can be fully tested by running `make fmt` and `make lint` on the codebase and verifying all files conform to the defined standards without manual intervention.

**Acceptance Scenarios**:

1. **Given** a developer has unformatted Python code, **When** they run `make fmt`, **Then** the code is automatically formatted according to ruff standards.

2. **Given** a PR with style violations, **When** the CI runs `make lint`, **Then** it fails with clear error messages indicating which files need formatting.

3. **Given** the project dependencies, **When** a new developer runs `pip install -r requirements-dev.txt`, **Then** ruff is installed and ready to use.

---

### User Story 2 - Ensure Safe Default Inference Backend (Priority: P1)

As a developer or CI system, I want the default inference backend to be `vllm` (local/OpenAI-compatible) rather than `auto`-selecting Gemini, so that the project doesn't accidentally use paid API services or leak API keys in development environments.

**Why this priority**: The current `auto` selection logic can silently switch to Gemini if `GOOGLE_API_KEY` is present, which violates security best practices and can incur unexpected costs.

**Independent Test**: Can be fully tested by running the evaluation pipeline without setting `GOOGLE_API_KEY` and verifying that vLLM is used as the backend.

**Acceptance Scenarios**:

1. **Given** a clean environment without `GOOGLE_API_KEY`, **When** the evaluation pipeline starts, **Then** it uses `vllm` as the professor backend.

2. **Given** an environment with `GOOGLE_API_KEY` set, **When** the evaluation pipeline starts, **Then** it still uses `vllm` as the default professor backend (unless explicitly overridden).

3. **Given** a developer wants to use Gemini for testing, **When** they set `AEGF_PROFESSOR_BACKEND=gemini` in `.env`, **Then** the pipeline uses Gemini as the professor backend.

---

### User Story 3 - Organize Merger Scripts (Priority: P2)

As a developer, I want merge scripts to be organized in `src/merger/` instead of being scattered in `data/weights/stage1_pure/` so that I can find and maintain them easily.

**Why this priority**: Scripts like `merge_shards.py`, `dna_*.py`, `check_alignment.py` are currently in the wrong location, making them hard to discover and maintain.

**Independent Test**: Can be fully tested by verifying that all merge-related scripts exist in `src/merger/` and can be imported as a Python module.

**Acceptance Scenarios**:

1. **Given** merge scripts are currently in `data/weights/stage1_pure/`, **When** they are moved to `src/merger/`, **Then** the directory structure is clean and all scripts are importable as `from src.merger import ...`.

2. **Given** a developer needs to merge LoRA adapters, **When** they look in `src/merger/`, **Then** they find `merge_shards.py` and related tools with clear documentation.

3. **Given** the Axolotl integration, **When** a developer runs the merge script, **Then** it produces an `adapter_model.safetensors` file compatible with Axolotl.

---

### User Story 4 - Enable Rapid Experimentation Pipeline (Priority: P3)

As a researcher, I want a fast experimental workflow that allows me to quickly test dataset variants and model configurations using cheap metrics (like BPB) so that I can iterate rapidly before committing to expensive full-scale training runs.

**Why this priority**: Rapid experimentation accelerates discovery of promising directions and prevents wasting resources on configurations that won't work.

**Independent Test**: Can be fully tested by running a complete experiment loop (generate variant → tokenize → train fast_mode → evaluate → report) in under 30 minutes.

**Acceptance Scenarios**:

1. **Given** a researcher wants to test a new dataset configuration, **When** they run the experiment orchestrator, **Then** it automatically generates the variant, tokenizes it, trains a small model, and evaluates it.

2. **Given** an experiment completes, **When** the researcher checks the results, **Then** they see `val_bpb`, `peak_vram_mb`, `mfu_percent`, and `total_tokens_M` in a structured report.

3. **Given** multiple experiment variants, **When** the researcher compares results, **Then** they can identify the best configuration in minutes rather than hours.

---

## Edge Cases

- What happens when a developer tries to use `gemini` backend without `GOOGLE_API_KEY` set?
  - System should fail gracefully with a clear error message explaining the requirement.

- What happens when the tokenizer training fails due to insufficient data?
  - System should checkpoint progress and allow resume from the last successful checkpoint.

- What happens when an experiment runs out of disk space?
  - System should detect low disk space and fail fast with a clear error message before corrupting checkpoints.

- How does the system handle the transition from `auto` to `vllm` default for existing users?
  - Provide a migration guide and allow override via `.env` or config file for backward compatibility.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST declare `ruff` as the canonical formatter in `pyproject.toml`, `requirements-dev.txt`, and all documentation.

- **FR-002**: The project MUST include `ruff>=0.9` in `requirements-dev.txt` to ensure developers can install all required tooling from a single file.

- **FR-003**: The system MUST set `DEFAULT_PROFESSOR_BACKEND = "vllm"` in `src/audit/config.py` instead of `"auto"`.

- **FR-004**: The system MUST set `professor_backend: "vllm"` in `configs/stage_5_evaluation/eval_config.yaml` as the default value.

- **FR-005**: The system MUST support overriding the professor backend via the `AEGF_PROFESSOR_BACKEND` environment variable.

- **FR-006**: The project MUST create `src/merger/` directory and move all merge-related scripts from `data/weights/stage1_pure/` to `src/merger/` (including `merge_shards.py`, `dna_*.py`, `check_alignment.py`, etc.).

- **FR-007**: The project MUST create `src/research/train_tokenizer.py` to train and save a canonical BPE tokenizer.

- **FR-008**: The project MUST create `src/audit/eval_bpb.py` to evaluate models using the BPB metric.

- **FR-009**: The project MUST create `src/research/experiment_orchestrator.py` to coordinate dataset variant generation, tokenization, training, and evaluation.

- **FR-010**: The project MUST create `docs/experiments.md` documenting the rapid experimentation workflow.

- **FR-011**: The project MUST create `configs/stage_4_training/axolotl/README.md` with tokenizer compatibility guidance for Axolotl.

- **FR-012**: The experiment pipeline MUST support parametrized dataset variants (e.g., `dedup_threshold`, `gold_injection_rate`, `min_length`, `sample_weighting`).

- **FR-013**: The experiment pipeline MUST register results in a structured format (TSV/DB) with metadata for each variant.

- **FR-014**: The fast-mode training MUST support small models, short TIME_BUDGET, few shards, and fixed validation shards.

### Key Entities *(include if feature involves data)*

- **ExperimentVariant**: Represents a unique combination of dataset parameters (dedup_threshold, gold_injection_rate, etc.) with metadata including creation timestamp, creator, and parent variant.

- **TrainingRun**: Represents a single training execution with metrics (val_bpb, peak_vram_mb, mfu_percent, total_tokens_M), configuration, and artifacts (model checkpoint, tokenizer).

- **TokenizerConfig**: Defines the canonical BPE tokenizer configuration including vocabulary size, byte-fallback settings, and added tokens.

- **ExperimentReport**: Aggregated results from an experiment run including comparison against baseline configurations and recommendations for next steps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `make fmt` on the entire codebase completes in under 30 seconds and reports zero style violations.

- **SC-002**: Installing development dependencies via `pip install -r requirements-dev.txt` includes ruff and all other required tools without additional installation steps.

- **SC-003**: The evaluation pipeline uses vLLM as the default professor backend in 100% of CI runs without requiring `GOOGLE_API_KEY`.

- **SC-004**: A developer can override the professor backend to Gemini by setting a single environment variable (`AEGF_PROFESSOR_BACKEND=gemini`) if needed for testing.

- **SC-005**: All references to `src/merger/` in documentation either point to an existing implementation or are removed with a clear migration note.

- **SC-006**: A researcher can run a complete experiment loop (generate → tokenize → train → evaluate → report) in under 30 minutes using fast_mode.

- **SC-007**: The experiment pipeline can compare 10 different dataset variants and identify the best configuration in under 5 minutes.

- **SC-008**: The documentation (`docs/experiments.md`) provides clear steps for a new researcher to run their first experiment in under 10 minutes.

- **SC-009**: The Axolotl README includes clear guidance on tokenizer compatibility with 3 documented options (use base, add tokens, expand embeddings) and their trade-offs.

- **SC-010**: Zero CI failures due to style violations after enforcing ruff formatting across the codebase.

---

## Clarificaciones

### Session 2026-03-18

- Q: ¿Qué scripts exactos debes mover a `src/merger/`? → A: Mover TODOS los .py de stage1_pure y stage2_final_consolidated (14 scripts total)

---

**Notes**:
- Items marked incomplete require spec updates before `/speckit.clarify` or `/speckit.plan`
- This specification focuses on WHAT users need and WHY, not HOW to implement (no tech stack, APIs, or code structure details)
- Written for business stakeholders and developers, not just technical implementation
