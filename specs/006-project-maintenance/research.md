# Research: Project Maintenance

**Date**: 2026-03-18  
**Feature**: 006-project-maintenance  
**Status**: Complete

## Decisions & Rationale

### Decision 1: Use ruff as canonical formatter

**What was chosen**: ruff>=0.9 as the single formatting and linting tool

**Rationale**: 
- ruff is already used in Makefile (`make fmt`, `make lint`)
- Extremely fast (100x faster than black + flake8 combined)
- Single tool for formatting, linting, and import sorting
- Compatible with existing project structure

**Alternatives considered**:
- black + isort + flake8: Slower, multiple tools to maintain
- autopep8: Less feature-complete, slower
- yapf: Google-specific, less community support

### Decision 2: Default backend = vllm

**What was chosen**: Change `DEFAULT_PROFESSOR_BACKEND` from "auto" to "vllm"

**Rationale**:
- "auto" selection can silently switch to Gemini if `GOOGLE_API_KEY` is present
- This violates security best practices (accidental API calls)
- vLLM is the project's primary inference backend (local, OpenAI-compatible)
- CI already uses vLLM exclusively

**Alternatives considered**:
- Keep "auto" but require explicit override: Risk of accidental Gemini usage
- Default to "gemini": Would incur unexpected costs

### Decision 3: Consolidate merger scripts

**What was chosen**: Move ALL Python scripts from `data/weights/stage1_pure/` and `data/weights/stage2_final_consolidated/` to `src/merger/`

**Rationale**:
- Scripts were scattered in data directories (wrong location)
- `src/merger/` is the canonical location for merge-related code
- Makes scripts importable as `from src.merger import ...`
- 14 scripts total (9 from stage1, 5 from stage2)

**Scripts to move**:
- stage1: `check_alignment.py`, `clean_dna.py`, `dna_fix_v2.py`, `dna_strict.py`, `final_ignition.py`, `merge_shards.py`, `repair_dna.py`, `repair_triple_dna.py`, `shotgun_dna.py`
- stage2: `analisis_avanzado.py`, `diagnostico.py`, `fusionar_final.py`, `repara_stage2.py`, `guardar_tokenizador.py`

### Decision 4: Rapid experimentation pipeline

**What was chosen**: Create 5 new files for fast experimentation:
1. `src/research/train_tokenizer.py` - Train BPE tokenizer
2. `src/audit/eval_bpb.py` - Evaluate BPB metric
3. `src/research/experiment_orchestrator.py` - Coordinate experiments
4. `docs/experiments.md` - Documentation
5. `configs/stage_4_training/axolotl/README.md` - Tokenizer guidance

**Rationale**:
- Current workflow requires full training runs (hours/days)
- Need fast iteration for dataset/config exploration
- BPB (bits per byte) is cheap metric for rapid validation
- Experiment orchestrator automates the full loop

**Alternatives considered**:
- Keep scripts scattered: Hard to discover and maintain
- Manual orchestration: Error-prone, time-consuming

## Unresolved Questions

None - all NEEDS CLARIFICATION items have been resolved.

## Next Steps

Proceed to Phase 1: Design & Contracts
1. Generate `data-model.md` with ExperimentVariant, TrainingRun, TokenizerConfig, ExperimentReport
2. Generate `quickstart.md` with rapid experimentation workflow
3. Update agent context via `.specify/scripts/bash/update-agent-context.sh copilot`
4. Re-evaluate Constitution Check post-design
