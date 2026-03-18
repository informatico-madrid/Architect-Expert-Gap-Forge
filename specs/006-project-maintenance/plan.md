# Implementation Plan: Project Maintenance

**Branch**: `006-project-maintenance` | **Date**: 2026-03-18 | **Spec**: [specs/006-project-maintenance/spec.md](specs/006-project-maintenance/spec.md)
**Input**: Feature specification from `/specs/006-project-maintenance/spec.md`

## Summary

Project maintenance to fix project organization, tooling, and defaults: move merger scripts to `src/merger/`, add ruff to dev dependencies, change default backend to vLLM, and create rapid experimentation pipeline.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: PyYAML>=6.0, pydantic>=2.0, pytest>=9.0, google-genai>=1.0, vllm, ruff>=0.9  
**Storage**: Files (safetensors, JSON, YAML configs)  
**Testing**: pytest with pytest-cov>=7.0, target >=90% coverage  
**Target Platform**: Linux server  
**Project Type**: ML training pipeline / data factory  
**Performance Goals**: Experiment loop <30 minutes, formatting <30 seconds  
**Constraints**: CI must use vLLM by default without GOOGLE_API_KEY  
**Scale/Scope**: 14 merger scripts, 5 new files for experimentation pipeline

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gates

| Requirement | Status | Check |
|-------------|--------|-------|
| No import-time side-effects | ✅ Enforced | All modules must have lazy imports |
| Logging with lazy formatting | ✅ Enforced | Use `logger.info("Loaded %d records", n)` |
| Strict typing | ✅ Enforced | All public functions must be annotated |
| No bare `except: pass` | ✅ Enforced | Explicit exceptions only |
| Header policy | ✅ Enforced | Python files must include AEGF header |
| SRP & module size | ✅ Enforced | Modules <400 LOC preferred |

**GATE STATUS**: ✅ PASS - No violations detected

### Post-Design Gates

| Requirement | Status | Check |
|-------------|--------|-------|
| ruff in requirements-dev.txt | ⚠️ Pending | Add `ruff>=0.9` |
| DEFAULT_PROFESSOR_BACKEND = "vllm" | ⚠️ Pending | Change from "auto" |
| src/merger/ exists | ⚠️ Pending | Create directory and move scripts |
| Experiment pipeline files | ⚠️ Pending | Create 5 new files |
| Error handling implemented | ⚠️ Pending | Tasks 1.3-1.5 |
| Data model implemented | ⚠️ Pending | Tasks 2.4-2.5 |
| Results registration | ⚠️ Pending | Task 6.6 |

**GATE STATUS**: ⚠️ PENDING - 7 items require implementation

## Project Structure

### Documentation (this feature)

```text
specs/006-project-maintenance/
├── plan.md              # This file
├── research.md          # Phase 0 output (NEEDS CLARIFICATION resolved)
├── data-model.md        # Phase 1 output (ExperimentVariant, TrainingRun, etc.)
├── quickstart.md        # Phase 1 output (rapid experimentation workflow)
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (implementation tasks)
```

### Source Code (repository root)

```text
src/
├── merger/              # NEW: All merge scripts moved from data/weights/
│   ├── __init__.py
│   ├── merge_shards.py
│   ├── check_alignment.py
│   ├── clean_dna.py
│   ├── dna_fix_v2.py
│   ├── dna_strict.py
│   ├── final_ignition.py
│   ├── repair_dna.py
│   ├── repair_triple_dna.py
│   ├── shotgun_dna.py
│   ├── analisis_avanzado.py
│   ├── diagnostico.py
│   ├── fusionar_final.py
│   ├── repara_stage2.py
│   └── guardar_tokenizador.py
├── research/            # NEW: Research utilities
│   ├── __init__.py
│   ├── train_tokenizer.py      # NEW: Train BPE tokenizer
│   └── experiment_orchestrator.py  # NEW: Coordinate experiments
├── audit/
│   ├── __init__.py
│   ├── eval_bpb.py             # NEW: Evaluate BPB metric
│   └── config.py               # MODIFY: Change DEFAULT_PROFESSOR_BACKEND
└── factory/
    └── [existing production modules]

configs/
├── stage_4_training/
│   └── axolotl/
│       └── README.md             # NEW: Tokenizer compatibility guidance
└── stage_5_evaluation/
    └── eval_config.yaml          # MODIFY: Change professor_backend to "vllm"

docs/
└── experiments.md                # NEW: Rapid experimentation workflow

requirements-dev.txt              # MODIFY: Add ruff>=0.9
```

### Structure Decision

Selected structure: Single project with organized submodules in `src/`.

- `src/merger/`: Consolidates all merge scripts from `data/weights/stage1_pure/` and `data/weights/stage2_final_consolidated/`
- `src/research/`: New module for research utilities (tokenizer training, experiment orchestration)
- `src/audit/`: Adds BPB evaluation utility and updates backend defaults
- `configs/`: Updates evaluation config and adds Axolotl tokenizer guidance
- `docs/`: Adds rapid experimentation documentation

## Complexity Tracking

No complexity violations detected. All changes follow existing patterns and constitution requirements.
