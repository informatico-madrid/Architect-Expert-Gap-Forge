# Tasks: Inference Calibration Suite (Stage 6)

**Feature**: Inference Calibration Suite  
**Branch**: 005-inference-calibration  
**Created**: 2026-03-15

---

## Phase 1: Setup

- [x] T001 Create calibration schema module in src/audit/calibration_schema.py
- [x] T002 [P] Add new dataclasses to schema.py: SamplingProfile, CalibrationResult, CalibrationReport, CalibrationCheckpoint
- [x] T003 [P] Create test fixtures for calibration in tests/fixtures/calibration_examples.json

---

## Phase 2: Foundational

- [x] T004 Implement SamplingProfile dataclass with validation in src/audit/calibration_schema.py
- [x] T005 Implement CalibrationResult dataclass in src/audit/calibration_schema.py
- [x] T006 Implement CalibrationReport dataclass in src/audit/calibration_schema.py
- [x] T007 Implement CalibrationCheckpoint dataclass in src/audit/calibration_schema.py
- [x] T008 [P] Add parameter grid constants (temperature, top_k, min_p, repetition_penalty) to calibration_schema.py

---

## Phase 3: User Story 1 - Automated Sampling Parameter Discovery [US1]

**Goal**: System automates parameter search through nested iteration  
**Independent Test**: Run with 5 test prompts, verify all parameter combinations are executed

### Core Implementation

- [x] T009 [US1] Implement calibration engine main loop in src/audit/calibration.py
- [x] T010 [US1] Implement profile generator (Cartesian product of parameter grids) in src/audit/calibration.py
- [x] T011 [US1] Implement response generator using InferenceRouter in src/audit/calibration.py
- [x] T012 [US1] Integrate with existing llm_judge_score function in src/audit/calibration.py

### Output Generation

- [x] T013 [US1] Implement calibration report JSON generation in src/audit/calibration.py
- [x] T014 [US1] Implement vllm_config.yaml generation in src/audit/calibration.py
- [x] T015 [US1] Implement best profile selection algorithm (highest aggregate score) in src/audit/calibration.py

---

## Phase 4: User Story 2 - Judge Integration [US2]

**Goal**: Each parameter combination is evaluated by Professor Judge  
**Independent Test**: Execute single iteration, verify Judge returns scores in expected format

### Scoring Logic

- [x] T016 [US2] Implement Composite Score calculation with SCORING_WEIGHTS in src/audit/calibration.py
- [x] T017 [US2] [P] Verify integration with existing judge module (src/audit/judge.py)
- [x] T018 [US2] Add error handling for Judge failures (log and continue)

---

## Phase 5: User Story 3 - Response Length Penalty [US3]

**Goal**: Responses shorter than 200 words receive proportional penalty  
**Independent Test**: Test with short response, verify adjusted_score < composite_score

### Penalty Implementation

- [x] T019 [US3] Implement word count calculation in src/audit/calibration.py
- [x] T020 [US3] Implement length penalty function (response_length < 200) in src/audit/calibration.py
- [x] T021 [US3] Apply penalty in CalibrationResult.adjusted_score calculation

---

## Phase 6: User Story 4 - Output Artifacts Generation [US4]

**Goal**: Generate calibration_report.json and vllm_config.yaml  
**Independent Test**: Run full calibration, verify both files exist with correct structure

### File Generation

- [x] T022 [US4] Implement JSON serialization for CalibrationReport in src/audit/calibration.py
- [x] T023 [US4] Implement YAML generation for vllm_config.yaml in src/audit/calibration.py
- [x] T024 [US4] Add output directory creation and file writing

---

## Phase 7: Polish & Cross-Cutting Concerns

### Resume Functionality

- [X] T025 Implement checkpoint save after each iteration in src/audit/calibration.py
- [X] T026 Implement resume logic (detect existing checkpoints) in src/audit/calibration.py
- [X] T027 Add --resume flag to CLI

### CLI Integration

- [x] T028 Extend src/audit/cli.py with calibrate subcommand
- [x] T029 Add CLI arguments: --prompts, --output-dir, --resume
- [x] T030 Add basic logging for progress (iteration, score)

### Documentation

- [x] T031 Update module docstrings in src/audit/calibration.py
- [x] T032 [P] Create example prompts file for testing

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

Phase 8 (Documentation)
  └─ T032 (complete) → T033 → T034 → T035

Phase 9 (US5 - Judge Calibration Analysis)
  └─ T035 (complete) → T036 → T037
  └─ T037 → T038 → T039 → T040
  └─ T040 → T041 → T042 → T043
  └─ T043 → T044 → T045 → T046
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

**Phase 9 (US5)**: Esta fase es opcional y añade inteligencia al sistema de calibración. Permite que el judge analice los campos `parameter_target` y `evaluation_focus` de los prompts para determinar qué parámetros ajustar automáticamente.

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
| Phase 9: Judge Calibration Analysis | 11 | US5 - Intelligent Parameter Adjustment |
| **Total** | **46** | **5** |

---

## Implementation Strategy

1. **Start with Setup and Foundational phases** - establish data structures
2. **Implement US1 (Parameter Discovery)** - core functionality
3. **Add US2-US4 incrementally** - each builds on previous
4. **Finish with Polish** - CLI integration and documentation
5. **Add Phase 8 (Documentation)** - update docs with Stage 6
6. **Implement Phase 9 (Judge Calibration Analysis)** - intelligent parameter adjustment using evaluation_focus
7. **Test after each phase** - ensure incremental progress

**MVP Definition**: Complete through Phase 3 (US1) + basic CLI = functional calibration loop with output files.

---

## Phase 8: Documentation Updates (per Clarifications)

- [x] T033 Update docs/METHODOLOGY.md with Stage 6 use cases and workflow
- [x] T034 Update README.md with new Stage 6 calibration section
- [x] T035 [P] Update any other relevant documentation files

---

## Phase 9: Judge Calibration Analysis (US5)

**Goal**: The judge uses parameter_target and evaluation_focus from calibration prompts to determine which parameters to modify and how
**Independent Test**: Run with calibration_prompts.example.yaml, verify the judge outputs parameter adjustment recommendations

### Prompt Parser Implementation

- [ ] T036 [US5] Implement CalibrationPrompt dataclass to parse parameter_target and evaluation_focus from prompts in src/audit/calibration_schema.py
- [ ] T037 [US5] [P] Add prompt loading from YAML with parameter extraction in src/audit/calibration.py

### Judge Analysis Engine

- [ ] T038 [US5] Implement parameter_target parser (extract target parameters: temperature, top_k, min_p, repetition_penalty, presence_penalty) in src/audit/calibration.py
- [ ] T039 [US5] Implement evaluation_focus analyzer to map focus areas to parameter adjustments in src/audit/calibration.py
- [ ] T040 [US5] Create mapping dictionary: evaluation_focus -> parameter adjustment strategy in src/audit/calibration.py

### Parameter Adjustment Logic

- [ ] T041 [US5] Implement generate_parameter_adjustments() based on evaluation_focus analysis in src/audit/calibration.py
- [ ] T042 [US5] Implement parameter refinement algorithm (narrow search space based on judge feedback) in src/audit/calibration.py
- [ ] T043 [US5] Add adaptive grid search that uses evaluation_focus to prioritize parameter combinations in src/audit/calibration.py

### Integration and Output

- [ ] T044 [US5] Integrate parameter_target/evaluation_focus analysis into calibration report in src/audit/calibration.py
- [ ] T045 [US5] Generate calibration_analysis.json with parameter adjustment recommendations in src/audit/calibration.py
- [ ] T046 [US5] Update CLI to support --use-prompt-metadata flag for intelligent calibration in src/audit/cli.py
