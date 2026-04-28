# Tasks: Frontend Discovery Enhancement - Verification

## Phase 1: Make It Work (POC)

Focus: Validate end-to-end that all fragment types (1,3,4,5) generate correctly across Python, TypeScript, PHP, and YAML repositories with per-file adapter selection.

- [x] 1.1 [P] Create fragment type verification test
  - **Do**: Create test that runs processor on sample repo and verifies TYPE 1, 3, 4, 5 bundles are emitted
  - **Files**: `tests/verification/test_fragment_types_verification.py`
  - **Done when**: Test exists that can validate fragment output
  - **Verify**: `python -m pytest tests/verification/test_fragment_types_verification.py -v` (will fail initially)
  - **Commit**: `test(verification): add fragment type verification test`
  - _Requirements: FR-1, FR-2, FR-3, FR-4_

- [x] 1.2 [P] Create per-file adapter selection test
  - **Do**: Create test that verifies `.ts` files route to TypeScriptAdapter, `.py` to PythonAstAdapter, `.php` to PhpLegacyAdapter
  - **Files**: `tests/verification/test_adapter_selection.py`
  - **Done when**: Test exists with per-file adapter routing verification
  - **Verify**: `python -m pytest tests/verification/test_adapter_selection.py -v` (will fail initially)
  - **Commit**: `test(verification): add per-file adapter selection test`
  - _Requirements: FR-5, AC-8.1 to AC-8.5_

- [x] 1.3 [P] Create MODULE_BLUEPRINT cross-language test
  - **Do**: Create test that verifies TYPE 4 MODULE_BLUEPRINT generation for Python, TypeScript, PHP, YAML repos
  - **Files**: `tests/verification/test_module_blueprint_cross_language.py`
  - **Done when**: Test exists with cross-language blueprint verification
  - **Verify**: `python -m pytest tests/verification/test_module_blueprint_cross_language.py -v` (will fail initially)
  - **Commit**: `test(verification): add MODULE_BLUEPRINT cross-language test`
  - _Requirements: FR-3, AC-3.1 to AC-3.7_

- [x] 1.4 [VERIFY] Quality checkpoint: lint and type check
  - **Do**: Run ruff lint and py_compile type check on new verification tests
  - **Verify**: `ruff check tests/verification/ && python -m py_compile tests/verification/*.py`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(verification): pass quality checkpoint`

- [x] 1.5 [P] Create TYPE 1 FUNCTIONAL_UNIT integration test
  - **Do**: Verify Type 1 bundle includes `[ARCH_HEADER]` with dependencies for Python + TypeScript repos
  - **Files**: `tests/integration/test_type1_functional_unit.py`
  - **Done when**: Test verifies TYPE 1 bundle structure and dependencies
  - **Verify**: `python -m pytest tests/integration/test_type1_functional_unit.py -v -k "test_types_1_to_5"`
  - **Commit**: `test(integration): add TYPE 1 FUNCTIONAL_UNIT test`
  - _Requirements: FR-1, AC-1.1 to AC-1.4_

- [x] 1.6 [VERIFY] POC checkpoint: verify fragment types work
  - **Do**: Run all fragment type verification tests to confirm end-to-end functionality
  - **Verify**: `python -m pytest tests/verification/ -v --tb=short`
  - **Done when**: All fragment types (1,3,4,5) verified working
  - **Commit**: `feat(verification): POC complete - all fragment types working`

## Phase 2: Refactoring

After POC validated, clean up test code and ensure adherence to project patterns.

- [x] 2.1 Extract test helper functions
  - **Do**: Extract common test fixtures and helpers from verification tests to `tests/fixtures/`
  - **Files**: `tests/fixtures/fragment_test_helpers.py`, refactor `tests/verification/*.py`
  - **Done when**: Tests use shared helpers, DRY principle applied
  - **Verify**: `python -m py_compile tests/fixtures/fragment_test_helpers.py`
  - **Commit**: `refactor(tests): extract common verification helpers`
  - _Design: Test Helper Pattern_

- [x] 2.2 Standardize test assertions
  - **Do**: Ensure all verification tests use consistent assertion patterns (bundle parsing, content checking)
  - **Files**: `tests/verification/*.py`, `tests/integration/*.py`
  - **Done when**: All tests follow same assertion pattern
  - **Verify**: `ruff check tests/verification/ tests/integration/`
  - **Commit**: `refactor(tests): standardize test assertions`
  - _Design: Testing Patterns_

- [x] 2.3 [VERIFY] Quality checkpoint: lint and type check
  - **Do**: Run ruff lint and py_compile on refactored test files
  - **Verify**: `ruff check tests/ && python -m py_compile tests/**/*.py`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(tests): pass quality checkpoint`

## Phase 3: Testing

Comprehensive test coverage for all fragment types, adapter selection, and cross-language scenarios.

- [x] 3.1 Unit test: TYPE 1 test file detection
  - **Do**: Create unit tests for test file mirror detection (exact name, tests/ directory)
  - **Files**: `tests/unit/test_test_file_detection.py`
  - **Done when**: Tests cover exact mirror + tests/ directory patterns
  - **Verify**: `python -m pytest tests/unit/test_test_file_detection.py -v`
  - **Commit**: `test(unit): add test file detection tests`
  - _Requirements: AC-1.2, FR-8_

- [x] 3.2 Unit test: SIZE gate filtering
  - **Do**: Create unit tests for MIN_SIZE (200) and LOGIC_ONLY_MIN_CHARS (1000) gates
  - **Files**: `tests/unit/test_size_gate.py`
  - **Done when**: Tests verify size filtering logic
  - **Verify**: `python -m pytest tests/unit/test_size_gate.py -v`
  - **Commit**: `test(unit): add size gate tests`
  - _Requirements: AC-2.1, AC-2.2, FR-10_

- [x] 3.3 Unit test: MODULE_BLUEPRINT anchor aggregation
  - **Do**: Create unit tests for anchor file aggregation (manifest.json, const.py, services.yaml)
  - **Files**: `tests/unit/test_module_blueprint_aggregation.py`
  - **Done when**: Tests verify anchor aggregation logic
  - **Verify**: `python -m pytest tests/unit/test_module_blueprint_aggregation.py -v`
  - **Commit**: `test(unit): add MODULE_BLUEPRINT aggregation tests`
  - _Requirements: AC-3.1 to AC-3.7, FR-3_

- [x] 3.4 Unit test: GOVERNANCE_RULES extraction
  - **Do**: Create unit tests for governance file detection at repo root (.codecov.yml, .gitlab-ci.yml)
  - **Files**: `tests/unit/test_governance_extraction.py`
  - **Done when**: Tests verify governance file detection
  - **Verify**: `python -m pytest tests/unit/test_governance_extraction.py -v`
  - **Commit**: `test(unit): add GOVERNANCE_RULES extraction tests`
  - _Requirements: AC-4.1 to AC-4.4, FR-4_

- [x] 3.5 Integration test: TypeScript repo processing
  - **Do**: Verify TypeScript repo (.ts/.tsx files) generates TYPE 3 LOGIC_ONLY + TYPE 4 MODULE_BLUEPRINT
  - **Files**: `tests/integration/test_typescript_repo_processing.py`
  - **Done when**: TypeScript processing verified end-to-end
  - **Verify**: `python -m pytest tests/integration/test_typescript_repo_processing.py -v`
  - **Commit**: `test(integration): add TypeScript repo processing test`
  - _Requirements: FR-5, AC-5.1 to AC-5.5_

- [x] 3.6 Integration test: PHP repo processing
  - **Do**: Verify PHP repo (.php files) generates TYPE 3 LOGIC_ONLY + TYPE 4 MODULE_BLUEPRINT
  - **Files**: `tests/integration/test_php_repo_processing.py`
  - **Done when**: PHP processing verified end-to-end
  - **Verify**: `python -m pytest tests/integration/test_php_repo_processing.py -v`
  - **Commit**: `test(integration): add PHP repo processing test`
  - _Requirements: FR-5, AC-7.1 to AC-7.4_

- [x] 3.7 Integration test: YAML/Jinja repo processing
  - **Do**: Verify YAML/Jinja repo (.yaml/.jinja files) generates TYPE 3 LOGIC_ONLY + TYPE 4 MODULE_BLUEPRINT
  - **Files**: `tests/integration/test_yaml_repo_processing.py`
  - **Done when**: YAML processing verified end-to-end
  - **Verify**: `python -m pytest tests/integration/test_yaml_repo_processing.py -v`
  - **Commit**: `test(integration): add YAML/Jinja repo processing test`
  - _Requirements: FR-5, AC-6.1 to AC-6.4_

- [x] 3.8 Integration test: Mixed-language repo
  - **Do**: Create mixed-language repo (Python + TypeScript config) and verify per-file adapter selection
  - **Files**: `tests/integration/test_mixed_language_repo.py`, `tests/fixtures/mixed-repo/`
  - **Done when**: Mixed-language repo processing verified
  - **Verify**: `python -m pytest tests/integration/test_mixed_language_repo.py -v`
  - **Commit**: `test(integration): add mixed-language repo test`
  - _Requirements: FR-5, AC-8.1 to AC-8.5_

- [x] 3.9 [VERIFY] Quality checkpoint: run all unit tests
  - **Do**: Run complete unit test suite to verify all unit tests pass
  - **Verify**: `python -m pytest tests/unit/ -v --tb=short`
  - **Done when**: All unit tests pass
  - **Commit**: `chore(tests): pass unit tests`

## Phase 4: Quality Gates

Ensure all quality gates pass before PR creation.

- [x] 4.1 Local quality check
  - **Do**: Run ALL quality checks locally before PR
  - **Verify**: All commands must pass:
    - Lint: `ruff check .`
    - Type check: `python -m py_compile src/**/*.py tests/**/*.py`
    - Tests: `python -m pytest tests/ -v --tb=short`
  - **Done when**: All commands pass with no errors
  - **Commit**: `fix(tests): address quality issues` (if fixes needed)

- [x] 4.2 AC checklist verification
  - **Do**: Programmatically verify each acceptance criterion is satisfied
  - **Verify**: Run specific test commands for each AC:
    - AC-1.1 to AC-1.4: `python -m pytest tests/ -v -k "functional_unit"`
    - AC-2.1 to AC-2.4: `python -m pytest tests/ -v -k "logic_only"`
    - AC-3.1 to AC-3.7: `python -m pytest tests/ -v -k "module_blueprint"`
    - AC-4.1 to AC-4.4: `python -m pytest tests/ -v -k "governance"`
    - AC-5.1 to AC-5.5: `python -m pytest tests/ -v -k "typescript"`
    - AC-6.1 to AC-6.4: `python -m pytest tests/ -v -k "yaml"`
    - AC-7.1 to AC-7.4: `python -m pytest tests/ -v -k "php"`
    - AC-8.1 to AC-8.5: `python -m pytest tests/ -v -k "adapter_selection"`
  - **Done when**: All acceptance criteria verified via automated checks
  - **Commit**: `chore(verification): AC checklist complete`

- [x] 4.3 Create PR and verify CI
  - **Do**:
    1. Verify current branch is feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin feat/frontend-discovery-enhancement`
    3. Create PR: `gh pr create --title "Verify frontend discovery enhancement" --body "Complete verification of fragment types 1,3,4,5 across all languages"`
  - **Verify**: `gh pr checks --watch` (wait for CI completion, all checks must show ✓)
  - **Done when**: CI pipeline passes, PR ready for review
  - **Commit**: None (PR created)

## Phase 5: PR Lifecycle

Continuous PR validation until all completion criteria met.

- [x] 5.1 Monitor CI and fix failures
  - **Do**: Watch CI pipeline, fix any failures (test regressions, coverage drops)
  - **Verify**: `gh pr checks` shows all green
  - **Done when**: All CI checks pass
  - **Commit**: `fix(tests): resolve CI failures` (if needed)

- [x] 5.2 Address review comments - commit
  - **Do**: Implement code review feedback, update tests as requested
  - **Verify**: `gh pr review --submit` after comments resolved
  - **Done when**: All review comments addressed
  - **Commit**: `feat(tests): address review comments`

- [x] 5.3 Final validation: zero regressions
  - **Do**: Confirm all existing tests still pass, no regressions introduced
  - **Verify**: `python -m pytest tests/ -v --tb=short && echo REgression_FREE`
  - **Done when**: Zero test regressions
  - **Commit**: None

- [x] 5.4 Final validation: modularity
  - **Do**: Verify test code is modular and reusable (not spec-specific hardcoding)
  - **Verify**: `ruff check tests/ && python -m py_compile tests/**/*.py`
  - **Done when**: Code is clean and follows project patterns
  - **Commit**: `refactor(tests): ensure modularity`

- [x] 5.5 E2E verification: real-world processing
  - **Do**: Process a real repository through the full pipeline and verify output
  - **Verify**: Run processor on sample repo, check fragment bundles in output
  - **Done when**: Real-world processing verified
  - **Commit**: None

- [ ] 5.6 PR merge readiness
  - **Do**: Confirm PR is merge-ready (all checks green, review approved)
  - **Verify**: `gh pr status` shows all green, `gh pr review` shows approved
  - **Done when**: PR ready to merge
  - **Commit**: None

## Notes

- POC shortcuts:
  - Verification tests focus on output structure validation, not exhaustive edge cases
  - Mixed-language repo test uses simple Python + TypeScript config structure
  - Test fixtures created in `tests/fixtures/` for reusability

- Production TODOs:
  - Consider adding performance benchmarks for large repos (NFR-4: ≥50 files/sec)
  - Add memory usage monitoring for large repo processing (NFR-2)
  - Consider adding parse error recovery integration tests for all policies (abort, skip, mark_and_continue, fallback)

## Files Created

- `tests/verification/test_fragment_types_verification.py` - Fragment type verification
- `tests/verification/test_adapter_selection.py` - Per-file adapter selection test
- `tests/verification/test_module_blueprint_cross_language.py` - Cross-language blueprint test
- `tests/integration/test_type1_functional_unit.py` - TYPE 1 integration test
- `tests/integration/test_typescript_repo_processing.py` - TypeScript repo test
- `tests/integration/test_php_repo_processing.py` - PHP repo test
- `tests/integration/test_yaml_repo_processing.py` - YAML/Jinja repo test
- `tests/integration/test_mixed_language_repo.py` - Mixed-language repo test
- `tests/unit/test_test_file_detection.py` - Test file detection unit test
- `tests/unit/test_size_gate.py` - Size gate unit test
- `tests/unit/test_module_blueprint_aggregation.py` - MODULE_BLUEPRINT aggregation test
- `tests/unit/test_governance_extraction.py` - GOVERNANCE_RULES extraction test

## Paths Referenced

- `/mnt/bunker_data/ai/data_factory/specs/frontend-discovery-enhancement/tasks.md` - This task file
- `/mnt/bunker_data/ai/data_factory/tests/` - Test directory root
- `/mnt/bunker_data/ai/data_factory/src/utils/extractors/` - Adapter implementations
- `/mnt/bunker_data/ai/data_factory/src/discovery/` - Discovery and processing logic

## Command Reference

**Run all verification tests:**
```bash
python -m pytest tests/verification/ -v --tb=short
```

**Run integration tests:**
```bash
python -m pytest tests/integration/ -v --tb=short
```

**Run unit tests:**
```bash
python -m pytest tests/unit/ -v --tb=short
```

**Quality checks:**
```bash
ruff check .
python -m py_compile src/**/*.py tests/**/*.py
```

**CI verification:**
```bash
gh pr checks --watch
```
