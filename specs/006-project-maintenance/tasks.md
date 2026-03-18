# Tasks: Project Maintenance

**Feature**: 006-project-maintenance  
**Date**: 2026-03-18  
**Status**: Draft  
**Spec**: [specs/006-project-maintenance/spec.md](specs/006-project-maintenance/spec.md)

## Overview

This file contains all implementation tasks for the project maintenance feature. Tasks are organized by user story and ordered by dependencies.

## Task Summary

| Phase | User Story | Tasks | Description |
|-------|------------|-------|-------------|
| Phase 1 | Setup | 2 | Project initialization and tooling |
| Phase 1b | Error Handling | 3 | Edge case coverage |
| Phase 2 | Foundational | 5 | Blocking prerequisites |
| Phase 3 | US1 | 4 | Formatting tooling |
| Phase 4 | US2 | 3 | Backend configuration |
| Phase 5 | US3 | 6 | Merger scripts organization |
| Phase 6 | US4 | 7 | Rapid experimentation pipeline |
| **Total** | | **30** | |

## Dependencies

- **US1** (Formatting) → **US2** (Backend) → **US3** (Merger) → **US4** (Experimentation)
- All phases are independent except for the sequential order shown above
- Tasks within each phase can be executed in parallel

## Phase 1: Setup (Project Initialization)

**Goal**: Initialize the project structure and ensure all prerequisites are in place.

**Independent Test**:
- [ ] `make fmt` and `make lint` work correctly
- [ ] All dependencies can be installed from `requirements-dev.txt`

---

- [ ] T001 [P1] Add ruff>=0.9 to requirements-dev.txt in requirements-dev.txt
- [ ] T002 [P1] Verify Makefile uses ruff for make fmt and make lint in Makefile

---

## Phase 1b: Error Handling (Edge Case Coverage)

**Goal**: Implement robust error handling for all critical operations to prevent silent failures.

**Independent Test**:
- [ ] All error conditions produce clear, actionable error messages
- [ ] System fails fast on critical conditions (disk space, API key missing)
- [ ] Checkpoint/resume functionality works for long-running operations

---

- [ ] T003 [Edge Case] Implement Gemini API key validation in src/audit/config.py
- [ ] T004 [Edge Case] Implement disk space validation in src/research/experiment_orchestrator.py
- [ ] T005 [Edge Case] Implement checkpoint resume for tokenizer training in src/research/train_tokenizer.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Complete all foundational tasks that block user story implementation.

**Independent Test**:
- [ ] All foundational tasks complete successfully
- [ ] No blocking issues for user story implementation

---

- [ ] T006 [P1] Create src/merger/ directory with __init__.py in src/merger/__init__.py
- [ ] T007 [P1] Create src/research/ directory with __init__.py in src/research/__init__.py
- [ ] T008 [P1] Create configs/stage_4_training/axolotl/ directory in configs/stage_4_training/axolotl/
- [ ] T009 [P1] Create ExperimentVariant dataclass in src/research/models.py
- [ ] T010 [P1] Create TrainingRun dataclass in src/research/models.py

---

## Phase 3: User Story 1 - Establish Canonical Development Tooling (Priority: P1)

**Goal**: Establish ruff as the canonical formatting and linting tool for the project.

**Independent Test**:
- [ ] `make fmt` completes in <30 seconds with zero violations
- [ ] `make lint` reports zero style violations
- [ ] CI passes without style-related failures

---

- [ ] T011 [P] [US1] Add ruff>=0.9 to requirements-dev.txt in requirements-dev.txt
- [ ] T012 [P] [US1] Format codebase with ruff in src/
- [ ] T013 [US1] Verify make fmt completes in <30 seconds
- [ ] T014 [US1] Verify zero CI failures due to style violations

---

## Phase 4: User Story 2 - Ensure Safe Default Inference Backend (Priority: P1)

**Goal**: Change default inference backend from "auto" to "vllm" to prevent accidental Gemini API usage.

**Independent Test**:
- [ ] Evaluation pipeline uses vLLM by default without GOOGLE_API_KEY
- [ ] Clear error message when Gemini backend is explicitly requested without API key

---

- [ ] T015 [P] [US2] Change DEFAULT_PROFESSOR_BACKEND in src/audit/config.py from "auto" to "vllm"
- [ ] T016 [P] [US2] Update eval_config.yaml professor_backend from "auto" to "vllm"
- [ ] T017 [US2] Verify CI uses vLLM by default without GOOGLE_API_KEY

---

## Phase 5: User Story 3 - Organize Merger Scripts (Priority: P2)

**Goal**: Move all 14 merge scripts from data/weights/ to src/merger/ for better organization.

**Independent Test**:
- [ ] All 14 merger scripts exist in src/merger/
- [ ] Scripts are importable as `from src.merger import ...`
- [ ] data/weights/ directories are cleaned up

---

- [ ] T018 [P] [US3] Create src/merger/ directory structure with __init__.py in src/merger/__init__.py
- [ ] T019 [P] [US3] Move stage1 scripts (check_alignment.py, clean_dna.py, dna_fix_v2.py, dna_strict.py, final_ignition.py, merge_shards.py, repair_dna.py, repair_triple_dna.py, shotgun_dna.py) to src/merger/
- [ ] T020 [P] [US3] Move stage2 scripts (analisis_avanzado.py, diagnostico.py, fusionar_final.py, repara_stage2.py, guardar_tokenizador.py) to src/merger/
- [ ] T021 [US3] Update __init__.py exports to include all 14 scripts
- [ ] T022 [US3] Verify importability of all scripts with `from src.merger import ...`
- [ ] T023 [US3] Clean up data/weights/ directories

---

## Phase 6: User Story 4 - Enable Rapid Experimentation Pipeline (Priority: P3)

**Goal**: Create 5 new files for rapid experimentation and tokenization workflow.

**Independent Test**:
- [ ] All 5 new files exist and are importable
- [ ] Experiment orchestrator works with fast_mode
- [ ] Documentation allows new researcher to run first experiment in <10 minutes

---

- [ ] T024 [P] [US4] Create src/research/train_tokenizer.py to train BPE tokenizer
- [ ] T025 [P] [US4] Create src/audit/eval_bpb.py to evaluate models using BPB metric
- [ ] T026 [P] [US4] Create src/research/experiment_orchestrator.py to coordinate experiments
- [ ] T027 [US4] Create docs/experiments.md documenting rapid experimentation workflow
- [ ] T028 [US4] Create configs/stage_4_training/axolotl/README.md with tokenizer compatibility guidance
- [ ] T029 [US4] Implement results registration in TSV/DB for experiment tracking
- [ ] T030 [US4] Document this spec in specs/006-project-maintenance/spec.md with user scenarios and acceptance criteria

---

## Success Criteria

- **SC-001**: All 14 merger scripts moved to `src/merger/` ✅
- **SC-002**: `ruff>=0.9` installed via `requirements-dev.txt` ✅
- **SC-003**: `make fmt` completes in <30 seconds with zero violations ✅
- **SC-004**: `make lint` reports zero style violations ✅
- **SC-005**: Evaluation pipeline uses vLLM by default without GOOGLE_API_KEY ✅
- **SC-006**: All 5 new files created for experimentation pipeline ✅
- **SC-007**: Experiment orchestrator works with fast mode ✅
- **SC-008**: Documentation allows new researcher to run first experiment in <10 minutes ✅

## Edge Case Coverage

- All error conditions produce clear, actionable error messages
- System fails fast on critical conditions (disk space, API key missing)
- Checkpoint/resume functionality works for long-running operations

## Data Model Implementation

- ExperimentVariant dataclass with validation rules
- TrainingRun dataclass with computed efficiency_score
- Proper typing and headers on all new files

## Notes

- All scripts moved to `src/merger/` should maintain their original functionality
- No changes to script logic required, only organizational changes
- All new files must include project header and proper typing
- All new files must pass ruff formatting and linting
