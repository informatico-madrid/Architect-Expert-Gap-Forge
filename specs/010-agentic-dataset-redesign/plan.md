# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

**Language/Version**: Python 3.11+ (enforced by repository root `pyproject.toml` and `requirements.txt`)  
**Primary Dependencies**: Pydantic (v2), PyYAML, requests (API client), aiohttp (async HTTP), click (CLI), pytest (testing), numpy (numerical ops), tqdm (progress bars)  
**Storage**: Local filesystem (JSONL files), checkpoint files (JSON), HuggingFace Hub (download anchor datasets)  
**Testing**: pytest with typed fixtures in `tests/`, coverage target >= 90% for `src/factory/` and `src/curation/`  
**Target Platform**: Linux server (Ubuntu 22.04+), GPU-enabled for training (not for Stage 2/3 generation)  
**Project Type**: Data pipeline / CLI tool (Stage 2 Factory + Stage 3 Curation)  
**Performance Goals**: Stage 2 generation: ~12–15k trajectories in <24h with API external; Stage 3 curation: <60s for 50k records  
**Constraints**: No silent failures (explicit exceptions), strict typing (Pydantic + type annotations), no import-time side effects, checkpoint resumption for Stage 2  
**Scale/Scope**: ~40k–50k total records (30% specialized HA trajectories, 70% anchor datasets), multi-turn conversations (3–10 turns per trajectory)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gates

- ✅ **Header Policy**: All new Python source files must include AEGF header (shebang, project identifier, copyright, SPDX license). CI enforces via `scripts/check_headers.py --check`.
- ✅ **Strict Typing**: All public functions and methods must be fully annotated; use `TypedDict`, `@dataclass(slots=True, frozen=True)`, and Pydantic models for structured data.
- ✅ **No Import-Time Side-Effects**: Module imports must not trigger I/O, network calls, or client instantiation.
- ✅ **Logging**: One `logger = logging.getLogger(__name__)` per module; lazy formatting (`logger.info("Loaded %d records", n)`).
- ✅ **Error Handling**: Explicit exceptions only; no bare `except: pass`; no `SystemExit` for flow-control.
- ✅ **Testing & Coverage**: Unit and integration tests required for new modules; coverage >= 90% for `src/factory/` and `src/curation/`.
- ✅ **Security**: No credentials in source; use environment variables and `.example` files for config templates.
- ✅ **DRY**: Duplicate logic must be extracted to shared modules.
- ✅ **No Silent Failures**: Parse or validation errors must raise explicit exceptions.

**Result**: All gates pass. No violations requiring justification.

### Post-Design Re-Evaluation

After Phase 1 design, re-evaluate Constitution Check for any new architectural patterns introduced (e.g., `TeacherModelClient` strategy, checkpoint persistence). Current plan anticipates no violations.

## Project Structure

### Documentation (this feature)

```text
specs/010-agentic-dataset-redesign/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── factory/
│   ├── agentic_teacher_client.py    # Strategy pattern: TeacherProviderStrategy + OpenAI/Anthropic/Gemini providers
│   ├── trajectory_generator.py      # Stage 2: generate HA trajectories; loads templates from configs/
│   ├── hard_query_builder.py        # Hard queries; templates from configs/stage_2_factory/prompts/
│   ├── schema.py                    # Factory-specific models: TurnType, TrajectoryMode, Turn, AgenticTrajectory
│   ├── config.py                    # config parsing: TeacherModelConfig, DatasetConfig
│   └── __init__.py
├── curation/
│   ├── dataset_mixer.py             # Stage 3: normalize, mix, shuffle, export single JSONL
│   ├── anchor_dataset_downloader.py # Download anchor datasets from HuggingFace Hub
│   ├── format_normalizer.py         # Convert all formats to ChatML (OpenAI Messages)
│   ├── dedup_and_validate.py        # Remove duplicates, validate no-call, composition report
│   └── __init__.py
├── training/
│   ├── config_validator.py          # validate_axolotl_neftune (alpha ∈ [5,15]); Stage 4 only
│   └── __init__.py
└── utils/
    ├── schema.py                    # Shared: DatasetRecord, CompositionReport, Message, RecordMetadata
    ├── exceptions.py                # Shared: ConfigValidationError, NormalizationError, DeduplicationError, TeacherAPIError
    ├── checkpoint.py                # Generic checkpoint base class (extended by src/factory/checkpoint.py)
    └── logging.py                   # get_logger(name) -> Logger helper

tests/
├── factory/
│   ├── test_trajectory_generator.py
│   ├── test_hard_query_builder.py
│   └── test_teacher_client.py
├── curation/
│   ├── test_dataset_mixer.py
│   ├── test_format_normalizer.py
│   └── test_dedup_validate.py
├── training/
│   └── test_config_validator.py
└── fixtures/
    ├── seed_examples.yaml
    └── anchor_dataset_samples/
```

**Structure Decision**: Separación en cuatro capas: `src/factory/` (Stage 2), `src/curation/` (Stage 3), `src/training/` (Stage 4 config validation), `src/utils/` (entidades y excepciones compartidas). `TeacherModelClient` usa Strategy pattern alineado con `src/audit/inference.py`. Templates de prompts externalizados en `configs/stage_2_factory/prompts/`. Todos los módulos nuevos siguen patrones AEGF: strict typing, no import-time side effects, un logger por módulo, tests >= 90% coverage.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations detected. Complexity tracking not required.*

---

## Summary

**Primary Requirement**: Redesign Stage 2 (Factory) and Stage 3 (Curation) of the synthetic data generation pipeline to produce high-quality, multi-turn agentic trajectories that solve the "tool laziness" problem in the Qwen3-30b-A3B model fine-tuned for Home Assistant 2026.

**Technical Approach**:

- **Stage 2 — Factory**: Generate ~12–15k specialized trajectories using an external API model (configurable: OpenAI-compatible, Anthropic, Gemini). Each trajectory contains 3–10 turns with backtracking (error injection + recovery), hard queries (abstract objectives), and no-call examples. Implement resilience via sleep configuration, exponential backoff with retries, and disk checkpointing for resume capability.

- **Stage 3 — Curation**: Download anchor datasets from HuggingFace Hub (`Salesforce/xlam-function-calling-60k`, `FineTome-100k`, `Magicoder`/`Stack-v2`), normalize all formats to ChatML (OpenAI Messages), mix at 30% specialized / 70% anchor, deduplicate, validate no-call constraints, and export a single deterministic JSONL file for Axolotl training.

**Key Constraints**:
- 30% specialized HA trajectories + 70% anchor general (standard SFT 2025–2026 recipe for tool-calling)
- Single JSONL output (no multi-dataset Axolotl config)
- `TeacherModelClient` via **Strategy pattern** (Protocol + OpenAIProvider/AnthropicProvider/GeminiProvider) alineado con `src/audit/inference.py`
- Prompt templates externalizados en `configs/stage_2_factory/prompts/` (constitución §IV)
- Shared entities (`DatasetRecord`, `CompositionReport`) en `src/utils/schema.py`; excepciones compartidas en `src/utils/exceptions.py`
- Validación Axolotl/NEFTune en `src/training/config_validator.py` (separado de Factory)
- Resilience: configurable sleep, backoff (max 5 retries, factor 2), checkpoint persistence
- Strict typing, no import-time side effects, 90%+ test coverage
- No credentials in source; environment variables for API keys

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
