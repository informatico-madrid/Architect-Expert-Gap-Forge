---

description: "Task list for Tests de Carga YAML para Ingestor"
---

# Tasks: Tests de Carga YAML para Ingestor

**Input**: Design documents from `/specs/013-ingestor-yaml-tests/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Tests are REQUIRED for this feature - the entire purpose is to add missing test coverage

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project - adjust based on plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify test environment and dependencies

**Independent Test**: N/A - Setup phase

- [ ] T001 Verify pytest is installed and run `pytest --version`
- [ ] T002 Verify pyyaml is installed and run `python -c "import yaml; print(yaml.__version__)"`
- [ ] T003 [P] Verify existing tests in tests/integration/ and tests/unit/ run correctly

**Checkpoint**: Test environment ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Understand existing test patterns and prepare fixtures

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Review existing tests in tests/unit/test_ingestor_profile_filter.py for test patterns
- [ ] T005 [P] Review existing tests in tests/integration/test_ingestor_git_recovery.py for patterns
- [ ] T006 Create test fixtures directory tests/fixtures/yaml_configs/ for test YAML files
- [ ] T007 Create sample valid YAML config file in tests/fixtures/yaml_configs/valid_config.yaml

**Checkpoint**: Test patterns understood, fixtures ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Tests de Carga YAML desde Disco (Priority: P1) 🎯 MVP

**Goal**: Create tests that load YAML files from disk using yaml.safe_load() to detect syntax errors before production

**Independent Test**: Create a YAML file with invalid syntax and verify the test fails

### Tests for User Story 1 (REQUIRED) ⚠️

- [ ] T008 [P] [US1] Integration test for valid YAML loading in tests/integration/test_ingestor_yaml_load.py
- [ ] T009 [P] [US1] Integration test for YAML with triple-dash bug in tests/integration/test_ingestor_yaml_load.py
- [ ] T010 [P] [US1] Integration test for invalid YAML syntax in tests/integration/test_ingestor_yaml_load.py

### Implementation for User Story 1

- [ ] T011 [US1] Create tests/fixtures/yaml_configs/valid_config.yaml with all required fields
- [ ] T012 [US1] Create tests/fixtures/yaml_configs/invalid_syntax.yaml with malformed YAML
- [ ] T013 [US1] Implement test_load_valid_yaml_from_disk() in tests/integration/test_ingestor_yaml_load.py
- [ ] T014 [US1] Implement test_load_yaml_with_triple_dash_bug() in tests/integration/test_ingestor_yaml_load.py
- [ ] T015 [US1] Implement test_load_invalid_yaml_syntax() in tests/integration/test_ingestor_yaml_load.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Tests de Validación de Configuración YAML Inválida (Priority: P1)

**Goal**: Validate that YAML files have all required fields for DiscoveryConfig model

**Independent Test**: Remove required field 'category' from YAML and verify test fails with ValidationError

### Tests for User Story 2 (REQUIRED) ⚠️

- [ ] T016 [P] [US2] Unit test for missing required field in tests/unit/test_ingestor_yaml_validation.py
- [ ] T017 [P] [US2] Unit test for invalid enum value in tests/unit/test_ingestor_yaml_validation.py

### Implementation for User Story 2

- [ ] T018 [US2] Create tests/fixtures/yaml_configs/missing_category.yaml without required field
- [ ] T019 [US2] Create tests/fixtures/yaml_configs/invalid_mode.yaml with invalid enum value
- [ ] T020 [US2] Implement test_missing_category_field_fails_validation() in tests/unit/test_ingestor_yaml_validation.py
- [ ] T021 [US2] Implement test_invalid_mode_fails_validation() in tests/unit/test_ingestor_yaml_validation.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Tests de Flujo CLI Completo (Priority: P2)

**Goal**: Create integration tests that execute full CLI flow from command to YAML loading to Pydantic

**Independent Test**: Run CLI with valid config and verify output is correct

### Tests for User Story 3 (REQUIRED) ⚠️

- [ ] T022 [P] [US3] Integration test for CLI with valid config in tests/integration/test_ingestor_cli.py
- [ ] T023 [P] [US3] Integration test for CLI with missing file in tests/integration/test_ingestor_cli.py

### Implementation for User Story 3

- [ ] T024 [US3] Implement test_cli_loads_valid_yaml_config() using click runner in tests/integration/test_ingestor_cli.py
- [ ] T025 [US3] Implement test_cli_fails_with_missing_file() using click runner in tests/integration/test_ingestor_cli.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: User Story 4 - Tests de Detección de Bugs Específicos (Priority: P1)

**Goal**: Create specific test that detects the bug where '---' after copyright header causes content to be ignored

**Independent Test**: Create YAML with '---' after copyright and verify test detects the issue

### Tests for User Story 4 (REQUIRED) ⚠️

- [ ] T026 [P] [US4] Integration test for YAML document separator bug in tests/integration/test_ingestor_yaml_load.py

### Implementation for User Story 4

- [ ] T027 [US4] Create tests/fixtures/yaml_configs/copyright_then_separator.yaml with '---' after copyright
- [ ] T028 [US4] Implement test_yaml_document_separator_ignores_content_before() to detect the bug in tests/integration/test_ingestor_yaml_load.py

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and coverage improvements

- [ ] T029 [P] Run all new tests with pytest and verify all pass
- [ ] T030 Run pytest with coverage: pytest --cov=src.discovery.ingestor --cov-report=html
- [ ] T031 Verify coverage meets >= 90% requirement for loader functions
- [ ] T032 [P] Update existing test documentation in tests/README.md if exists

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
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable
- **User Story 4 (P1)**: Can start after Foundational (Phase 2) - Tests the specific bug from US1

### Within Each User Story

- Tests are written first and MUST FAIL before implementation
- Fixtures before tests
- US1 complete before US4 (US4 builds on US1 patterns)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- US1 tests (T008-T010) can run in parallel
- US2 tests (T016-T017) can run in parallel
- US3 tests (T022-T023) can run in parallel
- US4 test (T026) is single task

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Integration test for valid YAML loading in tests/integration/test_ingestor_yaml_load.py"
Task: "Integration test for YAML with triple-dash bug in tests/integration/test_ingestor_yaml_load.py"
Task: "Integration test for invalid YAML syntax in tests/integration/test_ingestor_yaml_load.py"
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
5. Add User Story 4 → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3 + 4
3. Stories complete and integrate independently

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 32 |
| **User Stories** | 4 |
| **Parallelizable Tasks** | 15 |
| **MVP Scope** | User Story 1 (Phase 3) |

### Task Count per User Story

- **US1**: 8 tasks (T008-T015)
- **US2**: 6 tasks (T016-T021)
- **US3**: 4 tasks (T022-T025)
- **US4**: 3 tasks (T026-T028)
- **Setup**: 3 tasks (T001-T003)
- **Foundational**: 4 tasks (T004-T007)
- **Polish**: 4 tasks (T029-T032)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests MUST be written first and FAIL before implementation for TDD approach
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
