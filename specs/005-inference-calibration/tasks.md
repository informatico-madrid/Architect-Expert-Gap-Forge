# Tasks: Inference Calibration Suite (Stage 6)

**Feature**: Inference Calibration Suite  
**Branch**: 005-inference-calibration  
**Created**: 2026-03-15

---

## Phase 1: Setup

- [ ] T001 Create calibration schema module in src/audit/calibration_schema.py
- [ ] T002 [P] Add new dataclasses to schema.py: SamplingProfile, CalibrationResult, CalibrationReport, CalibrationCheckpoint
- [ ] T003 [P] Create test fixtures for calibration in tests/fixtures/calibration_examples.json

---

## Phase 2: Foundational

- [ ] T004 Implement SamplingProfile dataclass with validation in src/audit/calibration_schema.py
- [ ] T005 Implement CalibrationResult dataclass in src/audit/calibration_schema.py
- [ ] T006 Implement CalibrationReport dataclass in src/audit/calibration_schema.py
- [ ] T007 Implement CalibrationCheckpoint dataclass in src/audit/calibration_schema.py
- [ ] T008 [P] Add parameter grid constants (temperature, top_k, min_p, repetition_penalty) to calibration_schema.py

---

## Phase 3: User Story 1 - Automated Sampling Parameter Discovery [US1]

**Goal**: System automates parameter search through nested iteration  
**Independent Test**: Run with 5 test prompts, verify all parameter combinations are executed

### Core Implementation

- [ ] T009 [US1] Implement calibration engine main loop in src/audit/calibration.py
- [ ] T010 [US1] Implement profile generator (Cartesian product of parameter grids) in src/audit/calibration.py
- [ ] T011 [US1] Implement response generator using InferenceRouter in src/audit/calibration.py
- [ ] T012 [US1] Integrate with existing llm_judge_score function in src/audit/calibration.py

### Output Generation

- [ ] T013 [US1] Implement calibration report JSON generation in src/audit/calibration.py
- [ ] T014 [US1] Implement vllm_config.yaml generation in src/audit/calibration.py
- [ ] T015 [US1] Implement best profile selection algorithm (highest aggregate score) in src/audit/calibration.py

---

## Phase 4: User Story 2 - Judge Integration [US2]

**Goal**: Each parameter combination is evaluated by Professor Judge  
**Independent Test**: Execute single iteration, verify Judge returns scores in expected format

### Scoring Logic

- [ ] T016 [US2] Implement Composite Score calculation with SCORING_WEIGHTS in src/audit/calibration.py
- [ ] T017 [US2] [P] Verify integration with existing judge module (src/audit/judge.py)
- [ ] T018 [US2] Add error handling for Judge failures (log and continue)

---

## Phase 5: User Story 3 - Response Length Penalty [US3]

**Goal**: Responses shorter than 200 words receive proportional penalty  
**Independent Test**: Test with short response, verify adjusted_score < composite_score

### Penalty Implementation

- [ ] T019 [US3] Implement word count calculation in src/audit/calibration.py
- [ ] T020 [US3] Implement length penalty function (response_length < 200) in src/audit/calibration.py
- [ ] T021 [US3] Apply penalty in CalibrationResult.adjusted_score calculation

---

## Phase 6: User Story 4 - Output Artifacts Generation [US4]

**Goal**: Generate calibration_report.json and vllm_config.yaml  
**Independent Test**: Run full calibration, verify both files exist with correct structure

### File Generation

- [ ] T022 [US4] Implement JSON serialization for CalibrationReport in src/audit/calibration.py
- [ ] T023 [US4] Implement YAML generation for vllm_config.yaml in src/audit/calibration.py
- [ ] T024 [US4] Add output directory creation and file writing

---

## Phase 7: Polish & Cross-Cutting Concerns

### Resume Functionality

- [ ] T025 Implement checkpoint save after each iteration in src/audit/calibration.py
- [ ] T026 Implement resume logic (detect existing checkpoints) in src/audit/calibration.py
- [ ] T027 Add --resume flag to CLI

### CLI Integration

- [ ] T028 Extend src/audit/cli.py with calibrate subcommand
- [ ] T029 Add CLI arguments: --prompts, --output-dir, --resume
- [ ] T030 Add basic logging for progress (iteration, score)

### Documentation

- [ ] T031 Update module docstrings in src/audit/calibration.py
- [ ] T032 [P] Create example prompts file for testing

---

## Dependency Graph

```
Phase 1 (Setup)
  └─ T001 → T002, T003

Phase 2 (Foundational)
  ├─ T002 → T004, T005, T006, T007
  └─ T003 → (test fixtures ready)

Phase 3 (US1 - Parameter Discovery)
  ├─ T004, T005, T006, T007 → T009
  ├─ T009 → T010 → T011 → T012
  └─ T012 → T013 → T014 → T015

Phase 4 (US2 - Judge Integration)
  └─ T012 (complete) → T016 → T017 → T018

Phase 5 (US3 - Length Penalty)
  └─ T018 (complete) → T019 → T020 → T021

Phase 6 (US4 - Output Artifacts)
  └─ T021 (complete) → T022 → T023 → T024

Phase 7 (Polish)
  └─ T015 (complete) → T025 → T026 → T027 → T028 → T029 → T030 → T031 → T032
```

---

## Parallel Opportunities

- **T002, T003**: Can run in parallel (different files)
- **T004-T008**: Can run in parallel (different dataclasses)
- **T019-T021**: Can run in parallel (different penalty functions)
- **T022-T024**: Can run in parallel (different output formats)

---

## MVP Scope (User Story 1 Only)

Para un MVP mínimo, completar:
- Phase 1: T001, T002
- Phase 2: T004-T008
- Phase 3: T009-T015
- Phase 7: T028-T030

Esto permite ejecutar la calibración básica y obtener resultados. Las historias US2-US4 pueden implementarse incrementalmente.

---

## Summary

| Phase | Tasks | User Story |
|-------|-------|------------|
| Phase 1: Setup | 3 | - |
| Phase 2: Foundational | 5 | - |
| Phase 3: US1 | 7 | Parameter Discovery |
| Phase 4: US2 | 3 | Judge Integration |
| Phase 5: US3 | 3 | Length Penalty |
| Phase 6: US4 | 3 | Output Artifacts |
| Phase 7: Polish | 8 | Cross-cutting |
| Phase 8: Documentation | 3 | Documentation updates |
| **Total** | **35** | **4** |

---

## Implementation Strategy

1. **Start with Setup and Foundational phases** - establish data structures
2. **Implement US1 (Parameter Discovery)** - core functionality
3. **Add US2-US4 incrementally** - each builds on previous
4. **Finish with Polish** - CLI integration and documentation
5. **Test after each phase** - ensure incremental progress

**MVP Definition**: Complete through Phase 3 (US1) + basic CLI = functional calibration loop with output files.

---

## Phase 8: Documentation Updates (per Clarifications)

- [ ] T033 Update docs/METHODOLOGY.md with Stage 6 use cases and workflow
- [ ] T034 Update README.md with new Stage 6 calibration section
- [ ] T035 [P] Update any other relevant documentation files
