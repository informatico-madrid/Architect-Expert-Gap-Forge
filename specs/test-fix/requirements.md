# Requirements: Fix All Test Failures and Collection Errors

## Goal

Fix all test failures and collection errors on the rfactory-factory-frameworks branch by modifying only tests/ and conftest.py files. Zero new failures. Every test must assert real behavior from source code.

## User Stories

### US-1: Test Suite Collects Without Errors
**As a** developer running the test suite
**I want to** collect all test files without collection errors
**So that** I can run pytest without `--continue-on-collection-errors`

**Acceptance Criteria:**
- [ ] AC-1.1: All test files import successfully (no ImportError, SyntaxError)
- [ ] AC-1.2: All test classes instantiate correctly at collection time
- [ ] AC-1.3: All fixtures referenced in test files are defined in conftest.py or the test module itself
- [ ] AC-1.4: `pytest --collect-only` completes with zero collection errors

### US-2: Test Setup Completes Without Errors
**As a** developer running a specific test file
**I want to** have all test fixtures available at setup time
**So that** tests begin execution without fixture resolution failures

**Acceptance Criteria:**
- [ ] AC-2.1: All test fixtures referenced by test files are defined (in conftest.py or test files)
- [ ] AC-2.2: Fixtures that depend on other fixtures resolve correctly
- [ ] AC-2.3: No fixture constructor raises exceptions during setup
- [ ] AC-2.4: `pytest --setup-only` completes with zero errors for every test file

### US-3: All VLLM Provider Tests Pass
**As a** developer verifying provider error handling
**I want to** have all VLLMProvider and VLLMProviderGenerate tests pass
**So that** I have confidence in provider error handling, retries, and fallback logic

**Acceptance Criteria:**
- [ ] AC-3.1: All tests that instantiate VLLMProvider set `VLLM_API_KEY` env var
- [ ] AC-3.2: Tests that mock HTTP errors use `requests.HTTPError` (not bare `Exception`)
- [ ] AC-3.3: Mock responses match actual VLLMProvider JSON parsing expectations
- [ ] AC-3.4: All 10 VLLMProvider failures in test_providers.py pass
- [ ] AC-3.5: All 10 VLLMProvider failures in test_edge_cases.py pass

### US-4: All Provider Test Assertions Match Source Code
**As a** developer verifying provider implementations
**I want to** have all provider test assertions match actual source code behavior
**So that** failing tests reflect real source code issues, not incorrect test expectations

**Acceptance Criteria:**
- [ ] AC-4.1: GeminiProvider test uses mock APIError (not direct instantiation)
- [ ] AC-4.2: All mock return types match actual function signatures
- [ ] AC-4.3: All 12 failures in test_providers.py pass
- [ ] AC-4.4: All 10 failures in test_edge_cases.py pass

### US-5: Non-Existent Feature Tests Removed
**As a** developer reading test results
**I want to** have no tests that assert features not implemented in source code
**So that** test failures always reflect real bugs, not missing test implementation

**Acceptance Criteria:**
- [ ] AC-5.1: Tests for removed `_detect_strategy` are removed or rewritten to test the actual discovery API
- [ ] AC-5.2: Tests for yaml/jinja adapters in the factory registry are removed (registry does not support these)
- [ ] AC-5.3: Tests asserting DSPy integration in HardQueryBuilder are removed (no DSPy in implementation)
- [ ] AC-5.4: Tests asserting forbidden_terms comment in source file are removed (comment does not exist)
- [ ] AC-5.5: Tests asserting example config file headers are removed or rewritten for actual headers

### US-6: Missing Test Fixtures Added
**As a** developer writing new tests
**I want to** have the `fixtures_dir` fixture available in conftest.py
**So that** test files can reference fixture data directories without defining their own

**Acceptance Criteria:**
- [ ] AC-6.1: `fixtures_dir` fixture defined in conftest.py pointing to tests/fixtures/
- [ ] AC-6.2: test_jinja_adapter.py all 10 tests pass after fixture is added
- [ ] AC-6.3: test_yaml_adapter.py all 11 tests pass after fixture is added

### US-7: Test Setup State Correct
**As a** developer running tests
**I want to** have all test setup state properly configured (env vars, monkeypatches, taxonomy)
**So that** tests execute against the correct preconditions

**Acceptance Criteria:**
- [ ] AC-7.1: NeMo pipeline tests monkeypatch `_NEMO_AVAILABLE = False` when testing not-installed path
- [ ] AC-7.2: Production v11 extra test has taxonomy loaded before asserting blueprint context
- [ ] AC-7.3: DSPy judge integration tests configure mock LM before calling `get_predict()`
- [ ] AC-7.4: All 6 "missing setup" test failures pass

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Fix 3 collection errors from removed `_detect_strategy` | High | Tests that import `_detect_strategy` removed or rewritten |
| FR-2 | Fix 21 setup errors from missing `fixtures_dir` fixture | High | Add `fixtures_dir` fixture to conftest.py, all jinja/yaml adapter tests pass |
| FR-3 | Fix 20 VLLM provider test failures (missing env var) | High | Add `monkeypatch.setenv("VLLM_API_KEY", "...")` to all VLLMProvider tests |
| FR-4 | Fix 2 wrong mock type failures | High | Replace bare `Exception` with `requests.HTTPError` in affected tests |
| FR-5 | Fix 1 Gemini APIError test (wrong constructor args) | High | Use mock APIError instead of direct instantiation |
| FR-6 | Fix 6 factory registry test failures (yaml/jinja adapters) | High | Remove tests for adapters not in registry |
| FR-7 | Fix 1 forbidden_terms test (asserts non-existent comment) | Medium | Remove test or rewrite to assert actual code behavior |
| FR-8 | Fix 1 HardQueryBuilder test (asserts DSPy that doesn't exist) | Medium | Remove test or rewrite for actual string-substitution behavior |
| FR-9 | Fix 1 example_configs test (asserts non-existent file header) | Medium | Remove test or rewrite for actual file header |
| FR-10 | Fix 1 production_v11_extra test (missing taxonomy) | Medium | Add taxonomy loading in test or rewrite assertion |
| FR-11 | Fix 2 NeMo pipeline test failures (missing monkeypatch) | Medium | Add `monkeypatch.setattr` for `_NEMO_AVAILABLE` |
| FR-12 | Fix 2 DSPy judge integration test failures (missing LM config) | Medium | Configure mock DSPy LM in tests or remove |
| FR-13 | Preserve 5 pre-existing failures untouched | High | Do not modify test_audit_scorecard_submodule.py, test_model_evaluator_golden.py, test_discovery_processor_cli.py |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Test Quality | No weak assertions | Zero `assert True`, zero tautological asserts |
| NFR-2 | Test Quality | No test tricks | Zero `pytest.skip`, zero `pytest.mark.xfail`, zero `pragma: no cover` hacks |
| NFR-3 | Test Quality | Every test runnable | Zero collection errors, zero setup errors |
| NFR-4 | Scope Constraint | Source code unchanged | Zero modifications to src/ directory |
| NFR-5 | Test Quality | Every test asserts real behavior | Every assertion derived from actual source code logic |

## Glossary
- **Collection error**: ImportError, SyntaxError, or module-level error preventing pytest from discovering tests
- **Setup error**: Fixture initialization failure before test body executes
- **Pre-existing failure**: Test failure that existed on main branch before this spec; not in scope
- **VLLM API**: VLLMProvider class that generates text via an LLM endpoint
- **DSPy**: Deep Symbolic Programming framework, referenced in some tests but not implemented in source
- **Monkeypatch**: pytest fixture used to temporarily modify Python objects for testing

## Out of Scope
- Modifying any source code in src/ directory
- Modifying tests in test_discovery_processor_cli.py (pre-existing failure)
- Modifying tests in test_audit_scorecard_submodule.py (pre-existing failures)
- Modifying tests in test_model_evaluator_golden.py (pre-existing failures)
- Adding new tests beyond fixing existing ones
- Refactoring test structure or patterns
- Changing pytest configuration

## Dependencies
- `src/discovery/file_scanner.py` — `_detect_strategy` function removed; tests must be updated to match
- `src/factory/extractors/factory.py` — adapter registry lacks yaml/jinja entries; tests must be removed
- `src/factory/hard_query_builder.py` — no DSPy integration; tests asserting DSPy must be removed
- `src/curation/curator_pipeline.py` — `_NEMO_AVAILABLE` flag used by NeMo pipeline tests
- `conftest.py` — needs `fixtures_dir` fixture added

## Success Criteria
- `pytest -x --ignore=tests/test_agentic_gen.py` passes with exit code 0 (all non-pre-existing tests pass)
- Zero collection errors across all test files
- Zero setup errors across all test files
- Zero new test failures introduced
- All 5 pre-existing failures remain untouched (no modifications to their test files)
- No weak assertions in any test
- No test tricks (skip, xfail, pragma cache)
- Every test asserts real behavior from source code

## Verification Contract

**Project type**: fullstack

**Entry points**:
- `pytest --collect-only` — collect all tests, zero errors
- `pytest -x --ignore=tests/test_agentic_gen.py` — run tests stop-on-first-failure, exit 0
- `pytest --continue-on-collection-errors` — run all tests, count failures
- Individual test files: test_providers.py, test_edge_cases.py, test_factory_yaml_jinja.py, test_jinja_adapter.py, test_yaml_adapter.py, test_auto_detection.py, test_auto_integration.py, test_e2e_auto_detection.py, test_forbidden_terms.py, test_hard_query_builder_cot.py, test_production_v11_extra.py, test_nemo_curator_suite.py, test_nemo_curator_suite_extra.py, test_judge_dspy_integration.py, test_example_configs.py

**Observable signals**:
- PASS: `pytest -x --ignore=tests/test_agentic_gen.py` returns exit code 0
- PASS: `pytest --collect-only --ignore=tests/test_agentic_gen.py` shows zero errors
- PASS: All modified test files show `passed` in summary
- FAIL: `pytest -x` returns non-zero (first failure stops execution)
- FAIL: Collection errors shown during `pytest --collect-only`
- FAIL: Setup errors shown as `ERROR at setup of ...`

**Hard invariants**:
- Source code in src/ must not be modified
- test_discovery_processor_cli.py must not be modified
- test_audit_scorecard_submodule.py must not be modified
- test_model_evaluator_golden.py must not be modified
- test_agentic_gen.py must remain ignored
- conftest.py modifications must not break existing fixtures

**Seed data**:
- tests/fixtures/yaml_samples/blueprint.yaml must exist
- tests/fixtures/jinja_samples/template.jinja must exist
- VLLM_API_KEY env var must be settable via monkeypatch
- _NEMO_AVAILABLE must be monkeypatchable in curator_pipeline module

**Dependency map**:
- conftest.py — shared fixtures used by all test files
- src/discovery/file_scanner.py — source of `_detect_strategy` removal
- src/factory/extractors/factory.py — adapter registry tested by factory_yaml_jinja
- src/factory/hard_query_builder.py — HardQueryBuilder tested by test_hard_query_builder_cot
- src/curation/curator_pipeline.py — NeMo pipeline tested by test_nemo_curator_suite
- src/factory/dspy_utils.py — DSPy predictor tested by test_judge_dspy_integration
- src/factory/prompt_builder.py — taxonomy-dependent functions tested by test_production_v11_extra

**Escalate if**:
- Source code needs changes to make tests pass (e.g., adding yaml/jinja adapters, implementing DSPy, adding forbidden_terms comment) — tests must be removed instead
- Pre-existing failures are actually new failures (requires investigation of main branch state)
- Fixture removal causes other tests to break (e.g., removing test_auto_detection fixtures affects other tests)
- Monkeypatching `_NEMO_AVAILABLE` doesn't work (requires source investigation)

## Unresolved Questions
- Should the 3 tests referencing `_detect_strategy` be completely removed, or rewritten to test the public `discover_modules` API instead?
- Are the 5 pre-existing failures truly 5 (audit_scorecard has 3, model_evaluator_golden has 1, discovery_processor_cli has 1), or is the count different?
- Does removing tests for non-existent features (yaml/jinja adapters, DSPy integration) reduce test coverage below acceptable levels?
- Is the `fixtures_dir` fixture needed by any other test files beyond jinja_adapter and yaml_adapter?

## Next Steps
1. Add `fixtures_dir` fixture to conftest.py to fix 21 setup errors
2. Remove tests that import removed `_detect_strategy` (3 collection errors)
3. Fix VLLM API KEY env var in 20 test failures (test_providers.py, test_edge_cases.py)
4. Fix wrong mock types (Exception vs HTTPError, APIError) in 3 failures
5. Remove tests for non-existent factory registry adapters (6 failures)
6. Remove tests asserting non-existent source features (DSPy, forbidden_terms comment, example configs header) — 4 failures
7. Fix missing test setup (taxonomy, _NEMO_AVAILABLE, DSPy LM config) — 6 failures
8. Run `pytest -x --ignore=tests/test_agentic_gen.py` — if it stops, fix that failure and repeat
9. Verify zero failures with `pytest --continue-on-collection-errors`
