---

description: "Task list for improving code coverage to 90%+"
---

# Tasks: Mejorar Cobertura de Código

**Input**: Design documents from `/specs/012-mejorar-cobertura-code/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Este feature requiere crear tests unitarios para todos los módulos con cobertura < 90%.

**Organization**: Tasks están organizadas por user story para implementación independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Verify pytest and pytest-cov are installed in environment
- [x] T002 Review existing fixtures in tests/fixtures/ for reuse patterns
- [x] T003 [P] Create coverage baseline by running `make coverage` to document current state

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create fixture file for eval_bpb tests at tests/fixtures/eval_bpb_examples.json
- [x] T005 Create fixture file for anchor_dataset tests at tests/fixtures/anchor_dataset_examples.json
- [x] T006 Create fixture file for format_normalizer tests at tests/fixtures/format_normalizer_examples.json
- [x] T007 Create fixture file for dedup_and_validate tests at tests/fixtures/dedup_examples.json
- [x] T008 Create fixture file for dataset_mixer tests at tests/fixtures/dataset_mixer_examples.json
- [x] T009 [P] Create mock utilities for HuggingFace Hub at tests/fixtures/hf_hub_mock.py
- [x] T010 [P] Create mock utilities for inference clients at tests/fixtures/inference_mocks.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Aumentar cobertura de módulos con 0% cobertura (P1) 🎯 MVP

**Goal**: Implementar tests para todos los módulos con 0% de cobertura: eval_bpb.py, logging.py, cache_reset.py

**Independent Test**: `pytest --cov=src/audit/eval_bpb --cov=src/utils/logging --cov=src/utils/cache_reset --cov-report=term-missing` debe mostrar >= 90%

### Tests for User Story 1

- [x] T011 [P] [US1] Create tests for calculate_bpb in tests/audit/test_eval_bpb.py
- [x] T012 [P] [US1] Create tests for evaluate_bpb_scores in tests/audit/test_eval_bpb.py
- [x] T013 [P] [US1] Create tests for aggregate_bpb_metrics in tests/audit/test_eval_bpb.py
- [x] T014 [P] [US1] Create tests for get_logger in tests/utils/test_logging.py
- [x] T015 [P] [US1] Create tests for reset_all_caches in tests/utils/test_cache_reset.py
- [x] T016 [P] [US1] Create tests for log_memory_usage in tests/utils/test_cache_reset.py

### Implementation for User Story 1

- [x] T017 [US1] Verify all tests pass with `pytest tests/audit/test_eval_bpb.py tests/utils/test_logging.py tests/utils/test_cache_reset.py`
- [x] T018 [US1] Run coverage check: `pytest --cov=src/audit/eval_bpb --cov=src/utils/logging --cov=src/utils/cache_reset --cov-report=term-missing --cov-fail-under=90`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Mejorar cobertura de módulos con baja cobertura (P2)

**Goal**: Aumentar cobertura de anchor_dataset_downloader.py (20%), dedup_and_validate.py (40%), format_normalizer.py (54%), dataset_mixer.py (34%) a >= 90%

**Independent Test**: `pytest --cov=src/curation/anchor_dataset_downloader --cov=src/curation/dedup_and_validate --cov=src/curation/format_normalizer --cov=src/curation/dataset_mixer --cov-report=term-missing` debe mostrar >= 90%

### Tests for User Story 2

- [x] T019 [P] [US2] Create tests for AnchorDatasetDownloader.download in tests/curation/test_anchor_dataset_downloader.py
- [x] T020 [P] [US2] Create tests for AnchorDatasetDownloader.parse in tests/curation/test_anchor_dataset_downloader.py
- [x] T021 [P] [US2] Create tests for AnchorDatasetDownloader.subsample in tests/curation/test_anchor_dataset_downloader.py
- [x] T022 [P] [US2] Create tests for AnchorDatasetDownloader.export in tests/curation/test_anchor_dataset_downloader.py
- [x] T023 [P] [US2] Create tests for load_anchor_configs in tests/curation/test_anchor_dataset_downloader.py
- [x] T024 [P] [US2] Create tests for detect_tool_format in tests/curation/test_dedup_and_validate.py
- [x] T025 [P] [US2] Create tests for validate_record in tests/curation/test_dedup_and_validate.py
- [x] T026 [P] [US2] Create tests for deduplicate_record in tests/curation/test_dedup_and_validate.py
- [x] T027 [P] [US2] Create tests for _convert_alpaca in tests/curation/test_format_normalizer.py
- [x] T028 [P] [US2] Create tests for _convert_sharegpt in tests/curation/test_format_normalizer.py
- [x] T029 [P] [US2] Create tests for _convert_openai_messages in tests/curation/test_format_normalizer.py
- [x] T030 [P] [US2] Create tests for DatasetMixer.mix in tests/curation/test_dataset_mixer.py
- [x] T031 [P] [US2] Create tests for DatasetMixer.export in tests/curation/test_dataset_mixer.py
- [x] T032 [P] [US2] Create tests for DatasetMixer.generate_report in tests/curation/test_dataset_mixer.py

### Implementation for User Story 2

 - [ ] T033 [US2] Verify all tests pass with `pytest tests/curation/test_anchor_dataset_downloader.py tests/curation/test_dedup_and_validate.py tests/curation/test_format_normalizer.py tests/curation/test_dataset_mixer.py`
 - [ ] T034 [US2] Run coverage check: `pytest --cov=src/curation/anchor_dataset_downloader --cov=src/curation/dedup_and_validate --cov=src/curation/format_normalizer --cov=src/curation/dataset_mixer --cov-report=term-missing --cov-fail-under=90`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Mejorar cobertura de módulos con cobertura media (P3)

**Goal**: Aumentar cobertura de agentic_teacher_client.py (78%), factory/config.py (69%), hard_query_builder.py (74%), python_ast_adapter.py (71%), prompt_builder.py (86%) a >= 90%

**Independent Test**: `pytest --cov=src/factory/agentic_teacher_client --cov=src/factory/config --cov=src/factory/hard_query_builder --cov=src/utils/extractors/python_ast_adapter --cov=src/factory/prompt_builder --cov-report=term-missing` debe mostrar >= 90%

### Tests for User Story 3

- [x] T035 [P] [US3] Create tests for error handling in tests/factory/test_agentic_teacher_client.py
- [x] T036 [P] [US3] Create tests for config validation in tests/factory/test_factory_config.py
- [x] T037 [P] [US3] Create tests for all routes in tests/factory/test_hard_query_builder.py
- [x] T038 [P] [US3] Create tests for regex fallback in tests/utils/test_python_ast_adapter.py
- [x] T039 [P] [US3] Create tests for missing variable handling in tests/factory/test_prompt_builder.py

### Implementation for User Story 3

- [x] T040 [US3] Verify all tests pass with `pytest tests/factory/test_agentic_teacher_client.py tests/factory/test_factory_config.py tests/factory/test_hard_query_builder.py tests/utils/test_python_ast_adapter.py tests/factory/test_prompt_builder.py`
- [x] T041 [US3] Run coverage check: `pytest --cov=src/factory/agentic_teacher_client --cov=src/factory/config --cov=src/factory/hard_query_builder --cov=src/utils/extractors/python_ast_adapter --cov=src/factory/prompt_builder --cov-report=term-missing --cov-fail-under=90`

**Checkpoint**: All user stories should now be independently functional

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T042 [P] Run full coverage check: `make coverage`
- [x] T043 [P] Verify total coverage >= 90% in coverage.xml (ACHIEVED: 93.85% - coverage.xml shows 0.9385 line-rate)
- [x] T044 [P] Update .gitignore if any new fixture files need exclusion (NO CHANGE NEEDED - fixtures properly tracked, pycache already ignored)
- [x] T045 [P] Document coverage improvements in docs/coverage_report.md
- [] T046 [P] Test coverage ``make coverage` must reach 90%. total coverage 90% requiered
---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Create tests for calculate_bpb in tests/audit/test_eval_bpb.py"
Task: "Create tests for evaluate_bpb_scores in tests/audit/test_eval_bpb.py"
Task: "Create tests for aggregate_bpb_metrics in tests/audit/test_eval_bpb.py"
Task: "Create tests for get_logger in tests/utils/test_logging.py"
Task: "Create tests for reset_all_caches in tests/utils/test_cache_reset.py"
Task: "Create tests for log_memory_usage in tests/utils/test_cache_reset.py"

# Verify coverage after all tests complete:
pytest --cov=src/audit/eval_bpb --cov=src/utils/logging --cov=src/utils/cache_reset --cov-report=term-missing --cov-fail-under=90
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
