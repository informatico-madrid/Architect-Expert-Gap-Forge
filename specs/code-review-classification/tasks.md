# Tasks: code-review-classification — Code Review Fixes

## Execution Order

Tasks must be executed sequentially. Each task fixes specific issues from Group 1 of code-review-classification.md. Quality gates run every 3 tasks (QG-1 through QG-17).

**Quality Gate Check**: After QG-N, run party mode with full consensus: syntax check, ruff, all tests, spec compliance.

## Phase 1: Blockers & Missing Dependencies

### Task T-001: Fix SyntaxError in failed_sample_logger.py
**Issues**: #23
**Priority**: P0 — blocks all imports
**Do**:
1. Read `infrastructure/anchor_dataset/failed_sample_logger.py` line 51
2. Fix indentation mismatch causing SyntaxError
3. Verify: `python -m py_compile infrastructure/anchor_dataset/failed_sample_logger.py`
**Verify**: `python -c "import infrastructure.anchor_dataset.failed_sample_logger" && echo T-001_PASS`
**Quality Gate**: QG-1

### Task T-002: Fix Malformed JSON in index-state.json
**Issues**: #43
**Priority**: P0 — breaks parsers
**Do**:
1. Read `specs/.index/index-state.json`
2. Fix malformed JSON (lines 56-58, 64-66, 93-95)
3. Validate JSON: parse with Python json module
**Verify**: `python -c "import json; json.load(open('specs/.index/index-state.json')); print('JSON_VALID')"`
**Quality Gate**: QG-1

### Task T-003: Add Missing numpy Dependency
**Issues**: #59
**Priority**: P0 — import will fail
**Do**:
1. Add `numpy==2.4.4` to `requirements.txt`
2. Also add to `pyproject.toml` dependencies if present
**Verify**: `grep -q 'numpy==2.4.4' requirements.txt && echo T-003_PASS`
**Quality Gate**: QG-1

## Quality Gate QG-1: Blockers & Dependencies

**Party Mode Consensus Required** — all agents must approve:
- `python -m py_compile` on all infrastructure/ files
- `python -c "import infrastructure.anchor_dataset.failed_sample_logger"`
- `python -c "import json; json.load(open('specs/.index/index-state.json'))"`
- `grep -q 'numpy==2.4.4' requirements.txt`
- `ruff check infrastructure/anchor_dataset/failed_sample_logger.py`
- All existing tests pass: `pytest tests/ -x --tb=short`

---

## Phase 2: Security Fixes

### Task T-004: Remove Hardcoded API Key Fallback
**Issues**: #17
**Priority**: P0 — security vulnerability
**Do**:
1. Read `infrastructure/anchor_dataset/anchor_providers.py` line 68
2. Remove hardcoded fallback `or "sk-master-bunker-2026"`
3. Provider should require valid API key or raise clear error
4. Update docstring to document new behavior
**Verify**: `grep -q 'sk-master-bunker-2026' infrastructure/anchor_dataset/anchor_providers.py && exit 1 || echo T-004_PASS`
**Quality Gate**: QG-2

### Task T-005: Fix Symlink Security Check
**Issues**: #30
**Priority**: P0 — security vulnerability
**Do**:
1. Read `infrastructure/baselines/measure_mipro_compile_baseline.py` lines 207-211
2. Fix: check symlink status BEFORE calling resolve()
3. Ensure symlink target is within allowed directory
**Verify**: `python -c "from infrastructure.baselines.measure_mipro_compile_baseline import *; print('OK')"`
**Quality Gate**: QG-2

### Task T-006: Fix Silent Exception Swallowing in anchor_providers.py
**Issues**: #18
**Priority**: P0 — masks errors
**Do**:
1. Read `infrastructure/anchor_dataset/anchor_providers.py` lines 106-107
2. Replace generic `except Exception` with specific exception handling
3. Add logging for caught exceptions
4. Distinguish between network errors, parse errors, validation errors
**Verify**: `python -m py_compile infrastructure/anchor_dataset/anchor_providers.py && echo T-006_PASS`
**Quality Gate**: QG-2

---

## Quality Gate QG-2: Security Fixes

**Party Mode Consensus Required** — all agents must approve:
- No hardcoded credentials in source: `grep -r 'sk-master-bunker-2026' infrastructure/ ; test $? -ne 0`
- Symlink check uses proper security pattern
- Exception handling has specific types + logging
- `ruff check infrastructure/` passes
- All tests pass: `pytest tests/ -x --tb=short`

---

## Phase 3: Runtime Crashes — Infrastructure

### Task T-007: Fix Gemini API Message Roles
**Issues**: #19
**Priority**: P0 — API validation error
**Do**:
1. Read `infrastructure/anchor_dataset/anchor_providers.py` lines 194-197
2. Fix role swap: `system_prompt` → `role: "system"`, `user_prompt` → `role: "user"`
3. Remove invalid `role: "model"` for user input
**Verify**: `python -c "import infrastructure.anchor_dataset.anchor_providers; print('OK')"`
**Quality Gate**: QG-3

### Task T-008: Fix exists() → is_file() in anchor_dataset_schema.py
**Issues**: #16
**Priority**: P0 — crash on directories
**Do**:
1. Read `infrastructure/anchor_dataset/anchor_dataset_schema.py` line 87
2. Change `file_path.exists()` to `file_path.is_file()`
**Verify**: `python -m py_compile infrastructure/anchor_dataset/anchor_dataset_schema.py && echo T-008_PASS`
**Quality Gate**: QG-3

### Task T-009: Fix os.chdir() Side-Effect in rollback_check.py
**Issues**: #38
**Priority**: P0 — global state mutation
**Do**:
1. Read `infrastructure/rollback_check.py` line 243
2. Replace `os.chdir()` with `os.scandir()` or context manager
3. Use `pathlib.Path.glob()` or explicit path concatenation
**Verify**: `python -m py_compile infrastructure/rollback_check.py && echo T-009_PASS`
**Quality Gate**: QG-3

---

## Quality Gate QG-3: Runtime Crashes

**Party Mode Consensus Required** — all agents must approve:
- `ruff check infrastructure/` passes
- All imports succeed: `python -c "import infrastructure"` 
- No SyntaxErrors in infrastructure/
- All existing tests pass: `pytest tests/ -x --tb=short`

---

## Phase 4: Runtime Crashes — Source Code

### Task T-010: Fix Duplicate --force Flag in rollback_check.py
**Issues**: #36
**Priority**: P1 — CLI error
**Do**:
1. Read `infrastructure/rollback_check.py` line 121
2. Remove duplicate `--force` flag from argument parser
**Verify**: `python infrastructure/rollback_check.py --help | grep -c '\-\-force' | grep -q '1' && echo T-010_PASS`
**Quality Gate**: QG-4

### Task T-011: Fix Contradictory Error Message in rollback_check.py
**Issues**: #37
**Priority**: P1 — misleading error
**Do**:
1. Read `infrastructure/rollback_check.py` line 224
2. Align error message with actual flag behavior
**Verify**: `python -m py_compile infrastructure/rollback_check.py && echo T-011_PASS`
**Quality Gate**: QG-4

### Task T-012: Fix Unreachable Exception Block in dependency_check.py
**Issues**: #34
**Priority**: P1 — dead code
**Do**:
1. Read `infrastructure/dependency_check.py` lines 167-174
2. Move exception handling to where it's actually reachable
3. Fix logic flow so the catch block is reachable
**Verify**: `python -m py_compile infrastructure/dependency_check.py && echo T-012_PASS`
**Quality Gate**: QG-4

---

## Quality Gate QG-4: Source Code Runtime Fixes

**Party Mode Consensus Required** — all agents must approve:
- `ruff check infrastructure/` passes
- `python -m py_compile` on all changed files
- All imports succeed
- All tests pass: `pytest tests/ -x --tb=short`

---

## Phase 5: Runtime Crashes — Test & Source

### Task T-013: Fix Logic Inversion in dataset_mixer.py count_tokens
**Issues**: #134
**Priority**: P1 — TypeError crash
**Do**:
1. Read `src/curation/dataset_mixer.py` lines 112-118
2. Fix logic inversion in count_tokens
3. Ensure return value is correct type
**Verify**: `python -c "from src.curation.dataset_mixer import *; print('OK')"`
**Quality Gate**: QG-5

### Task T-014: Fix is_cascade Boolean in trajectory_generator.py
**Issues**: #139
**Priority**: P1 — wrong DSPy payload
**Do**:
1. Read `src/factory/trajectory_generator.py` line 208
2. Fix incorrect derivation of is_cascade boolean
3. Ensure payload sent to DSPy is correct
**Verify**: `python -c "from src.factory.trajectory_generator import *; print('OK')"`
**Quality Gate**: QG-5

### Task T-015: Fix Overlapping Regex in jinja_base.py
**Issues**: #143
**Priority**: P1 — duplicate token extraction
**Do**:
1. Read `src/utils/extractors/extractors/jinja_base.py` lines 227-230
2. Fix overlapping regex patterns to prevent duplicate extraction
3. Ensure each token is extracted exactly once
**Verify**: `python -m py_compile src/utils/extractors/extractors/jinja_base.py && echo T-015_PASS`
**Quality Gate**: QG-5

---

## Quality Gate QG-5: Source Code Fixes

**Party Mode Consensus Required** — all agents must approve:
- `ruff check src/` passes
- `python -m py_compile` on all changed files
- All imports succeed: `python -c "from src.curation.dataset_mixer import *"`
- All tests pass: `pytest tests/ -x --tb=short`

---

## Phase 6: API/Integration Fixes

### Task T-016: Fix Operator Precedence in curator_cli.py
**Issues**: #133
**Priority**: P1 — wrong filter rate
**Do**:
1. Read `src/curation/curator_cli.py` lines 617-622
2. Fix incorrect operator precedence in filter rate calculation
**Verify**: `python -m py_compile src/curation/curator_cli.py && echo T-016_PASS`
**Quality Gate**: QG-6

### Task T-017: Fix Unused Variable Delta in e2e_verification.py
**Issues**: #152
**Priority**: P1 — setpoint logic broken
**Do**:
1. Read `tests/e2e_verification.py` lines 330-333
2. Assign/return delta variable instead of leaving it unused
**Verify**: `python -m py_compile tests/e2e_verification.py && echo T-017_PASS`
**Quality Gate**: QG-6

### Task T-018: Fix Spanish Detection Regex in design.md
**Issues**: #121
**Priority**: P1 — wrong detection results
**Do**:
1. Read `specs/prompt-externalization/design.md` line 288
2. Fix flawed regex for Spanish text detection
3. Test regex against known Spanish/English corpora
**Verify**: `python -c "import re; assert re.match(r'<new_pattern>', 'Hola'); print('OK')"`
**Quality Gate**: QG-6

---

## Quality Gate QG-6: API & Logic Fixes

**Party Mode Consensus Required** — all agents must approve:
- All changed files compile: `python -m py_compile` on each
- `ruff check src/ tests/` passes
- All tests pass: `pytest tests/ -x --tb=short`

---

## Phase 7: Dependency/Config Fixes

### Task T-019: Fix Profile Config Contradiction
**Issues**: #11
**Priority**: P2 — config behavior
**Do**:
1. Read `configs/stage_1_discovery/examples/homeassistant_frontend.yaml` lines 21-24, 80-81
2. Either comment out `profile: typescript` OR update header comment to match
**Verify**: `grep -A2 'IMPORTANT.*DO NOT set.*profile' configs/stage_1_discovery/examples/homeassistant_frontend.yaml | grep -q 'Comment out' && echo T-019_PASS || grep -q 'profile: typescript' configs/stage_1_discovery/examples/homeassistant_frontend.yaml && exit 1 || echo T-019_PASS`
**Quality Gate**: QG-7

### Task T-020: Fix Auto-Detection Priority Docs
**Issues**: #12
**Priority**: P2 — misleading docs
**Do**:
1. Read `docs/auto-detection.md` lines 29, 47, 146
2. Update claims to match actual code behavior (TypeScript prioritized over Python)
**Verify**: `grep -q 'TypeScript is prioritized' docs/auto-detection.md && echo T-020_PASS`
**Quality Gate**: QG-7

### Task T-021: Fix dspy Version Notation Inconsistency
**Issues**: #15
**Priority**: P2 — doc inconsistency
**Do**:
1. Read `specs/dependency-compatibility/requirements.md` line 64
2. Change `dspy<=3.2.0` to `dspy==3.2.0` (matches line 21 exact pin)
**Verify**: `grep 'dspy' specs/dependency-compatibility/requirements.md | grep -v '<=' && echo T-021_PASS`
**Quality Gate**: QG-7

---

## Quality Gate QG-7: Config & Docs Fixes

**Party Mode Consensus Required** — all agents must approve:
- `ruff check` on all changed files
- All tests pass: `pytest tests/ -x --tb=short`
- Config files parse correctly
- Documentation is consistent

---

## Phase 8: Code Quality Fixes

### Task T-022: Fix Raw Reference Context in seed_synthesizer.py
**Issues**: #26
**Priority**: P2 — premature filtering
**Do**:
1. Read `infrastructure/anchor_dataset/seed_synthesizer.py` lines 71, 95
2. Fix raw reference content in context to prevent premature leakage filtering
**Verify**: `python -m py_compile infrastructure/anchor_dataset/seed_synthesizer.py && echo T-022_PASS`
**Quality Gate**: QG-8

### Task T-023: Fix Resume Logic Duplicate Prevention
**Issues**: #29
**Priority**: P2 — duplicate generation
**Do**:
1. Read `infrastructure/anchor_dataset_builder.py` line 332
2. Add tracking for previously failed samples to prevent regeneration
**Verify**: `python -m py_compile infrastructure/anchor_dataset_builder.py && echo T-023_PASS`
**Quality Gate**: QG-8

### Task T-024: Fix Key Error from Missing Taxonomy Key
**Issues**: #60
**Priority**: P2 — KeyError crash
**Do**:
1. Read `specs/_epics/aegf-infrastructure/research.md` lines 227-228
2. Add default handling or missing key handling in prompt_builder.py
**Verify**: `python -c "import infrastructure.anchor_dataset.prompt_builder; print('OK')"`
**Quality Gate**: QG-8

---

## Quality Gate QG-8: Code Quality

**Party Mode Consensus Required** — all agents must approve:
- `ruff check infrastructure/ src/` passes
- All imports succeed
- All tests pass: `pytest tests/ -x --tb=short`

---

## Phase 9: Test Infrastructure — Fixture Fixes

### Task T-025: Fix Test Fixture Key Typos
**Issues**: #103, #104
**Priority**: P2 — fixture data mismatch
**Do**:
1. Read `specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_typescript_module.json`
2. Fix module dependency key typos (lines 15, 35)
3. Read `specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_yaml_module.json`
4. Fix i18n_keys vs cover module mismatch (lines 89-96)
**Verify**: `python -c "import json; json.load(open('specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_typescript_module.json')); json.load(open('specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_yaml_module.json')); print('FIXTURES_VALID')"`
**Quality Gate**: QG-9

### Task T-026: Fix Hardcoded Paths in Test Setup
**Issues**: #106, #196
**Priority**: P2 — portability
**Do**:
1. Read `specs/frontend-discovery-enhancement/tests/verification/test_module_blueprint_cross_language.py` line 47
2. Replace absolute path with relative or environment-based path
3. Read `tests/unit/test_processor_config_validation.py` lines 49-51
4. Replace hardcoded PYTHONPATH with relative path or environment variable
**Verify**: `python -m py_compile tests/unit/test_processor_config_validation.py && echo T-026_PASS`
**Quality Gate**: QG-9

### Task T-027: Fix Duplicate Fixture Function in conftest.py
**Issues**: #149
**Priority**: P2 — shadowing
**Do**:
1. Read `tests/conftest.py` lines 136-139
2. Remove duplicate `_load_fixture` function definition
3. Keep the correct implementation
**Verify**: `python -c "from tests.conftest import *; print('OK')"`
**Quality Gate**: QG-9

---

## Quality Gate QG-9: Test Fixture Fixes

**Party Mode Consensus Required** — all agents must approve:
- All fixture files are valid JSON
- No hardcoded paths in test setup
- No duplicate function definitions
- `ruff check tests/` passes
- All tests pass: `pytest tests/ -x --tb=short`

---

## Phase 10: Test Quality — Assertion Fixes

### Task T-028: Fix Wrong Assertions in Test Files
**Issues**: #151, #168, #175, #185
**Priority**: P2 — wrong test validation
**Do**:
1. Read `tests/curation/test_dedup_validate.py` line 376 — fix incorrect substring check
2. Read `tests/fixtures/repos/ha_python_repo.py` line 45 — fix calculate_total mismatch
3. Read `tests/fixtures/repos/python_repo.py` line 65 — fix calculate_total mismatch
4. Read `tests/test_persisted_sample_ha_standards.py` line 49 — fix wrong path argument
**Verify**: `python -m py_compile tests/curation/test_dedup_validate.py tests/test_persisted_sample_ha_standards.py && echo T-028_PASS`
**Quality Gate**: QG-10

### Task T-029: Fix Tautological Assertions
**Issues**: #179, #180
**Priority**: P2 — useless tests
**Do**:
1. Read `tests/test_generate_sample_async.py` lines 97-100 — fix tautological assertion
2. Read `tests/test_model_evaluator_config_and_cli.py` line 178 — fix trivially true assertion
**Verify**: `python -m py_compile tests/test_generate_sample_async.py tests/test_model_evaluator_config_and_cli.py && echo T-029_PASS`
**Quality Gate**: QG-10

### Task T-030: Fix Weak/Missing Test Assertions
**Issues**: #154, #158, #160, #162
**Priority**: P2 — tests don't verify claimed behavior
**Do**:
1. Read `tests/factory/test_backtracking_detector_messages.py` lines 40-48 — add case-insensitivity check
2. Read `tests/factory/test_trajectory_generator_dspy.py` lines 39-43 — fix misleading fallback coverage claim
3. Read `tests/fixtures/jinja_samples/template.jinja` — fix climate entity state assumption
4. Read `tests/fixtures/python_samples/nested_imports.py` — fix fixture content mismatch
**Verify**: `python -m py_compile tests/factory/test_backtracking_detector_messages.py && echo T-030_PASS`
**Quality Gate**: QG-10

---

## Quality Gate QG-10: Test Assertion Fixes

**Party Mode Consensus Required** — all agents must approve:
- No tautological assertions (no assertion of True/always-true conditions)
- All assertions verify actual behavior
- All test files compile: `python -m py_compile` on each
- `ruff check tests/` passes
- All tests pass: `pytest tests/ -x --tb=short`

---

## Phase 11: Spec Documentation — Contradictions

### Task T-031: Fix Spec Logical Contradictions
**Issues**: #46, #67
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/002-agentic-preservation/plan.md` lines 20-22 — fix logical contradiction in AC
2. Read `specs/anchor-dataset/design.md` line 319 — fix contradiction in exception handling
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-11

### Task T-032: Fix Spec Node Count Inconsistencies
**Issues**: #48, #63
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/006-langgraph-graph/plan.md` line 14 — fix inconsistent node count
2. Read `specs/_epics/aegf-langgraph-inference/epic.md` line 48 — resolve node count mismatch (3 vs 4 names)
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-11

### Task T-033: Fix Spec Regex & Logging Contradictions
**Issues**: #73, #74
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/anchor-dataset/requirements.md` lines 21, 28, 202 — align id field regex patterns
2. Read `specs/anchor-dataset/requirements.md` lines 41, 226 — fix "warning at INFO level" contradiction
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-11

---

## Quality Gate QG-11: Spec Contradiction Fixes

**Party Mode Consensus Required** — all agents must approve:
- No logical contradictions remain in specs
- Regex patterns consistent across all specs
- Logging level specs corrected
- All spec files are valid markdown
- All code tests still pass: `pytest tests/ -x --tb=short`

---

## Phase 12: Spec Documentation — Validation Fixes

### Task T-034: Fix Spec Validation Issues
**Issues**: #70, #75, #77
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/anchor-dataset/plan.md` line 56 — fix invalid JSON Schema syntax for domain enum
2. Read `specs/anchor-dataset/requirements.md` lines 135, 161, 215 — fix os.fsync() usage (should use fd, not path)
3. Read `specs/baseline-measurement/plan.md` lines 32-63 — fix contradictory directory paths
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-12

### Task T-035: Fix Spec Verify Command Issues
**Issues**: #92, #93, #94
**Priority**: P3 — verify commands incomplete
**Do**:
1. Read `specs/dependency-compatibility/tasks.md` line 376 — fix T-09 verify command (fragile)
2. Read `specs/dependency-compatibility/tasks.md` line 305 — fix T-07 verify command (incomplete)
3. Read `specs/dspy-integration/requirements.md` line 131 — fix malformed API signature FR-005
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-12

### Task T-036: Fix Spec Duplicate & Value Issues
**Issues**: #95, #96, #97
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/dspy-integration/task_review.md` line 60 — fix duplicate task ID T1.5
2. Read `specs/frontend-discovery-enhancement/.progress.md` lines 116-117, 296-297 — fix value mismatches
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-12

---

## Quality Gate QG-12: Spec Validation Fixes

**Party Mode Consensus Required** — all agents must approve:
- All spec files parse as valid markdown
- All JSON in specs is valid
- All verify commands are executable
- All code tests pass: `pytest tests/ -x --tb=short`

---

## Phase 13: Spec Documentation — Template Fixes

### Task T-037: Fix Template Key & Placeholder Issues
**Issues**: #114, #115, #116
**Priority**: P3 — template correctness
**Do**:
1. Read `specs/prompt-externalization/adversarial-review-findings.md` lines 20-22 — fix .system vs .get(template)
2. Read `specs/prompt-externalization/adversarial-review-findings.md` — fix placeholder syntax inconsistency ($var vs {var})
3. Read `specs/prompt-externalization/adversarial-review-findings.md` line 22 — define or remove $tools_json variable
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-13

### Task T-038: Fix Template Localization & Protocol Issues
**Issues**: #117, #118, #127
**Priority**: P3 — template correctness
**Do**:
1. Read `specs/prompt-externalization/adversarial-review-findings.md` lines 9-10 — remove Spanish from forbidden_terms
2. Read `specs/prompt-externalization/adversarial-review-findings.md` — fix inconsistent output protocol across prompts
3. Read `specs/yaml-adapter/requirements.md` line 31 — fix YAML !input tag placement
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-13

### Task T-039: Fix Spec Syntax & Reference Issues
**Issues**: #123, #125, #127
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/prompt-externalization/requirements.md` line 17 — fix module reference syntax AC-1.3
2. Read `specs/prompt-externalization/research.md` line 148 — fix placeholder replacement stripping dollar signs
3. Read `specs/prompt-externalization/plan.md` lines 12, 62 — resolve prompt storage format contradiction
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-13

---

## Quality Gate QG-13: Template & Spec Fixes

**Party Mode Consensus Required** — all agents must approve:
- No hardcoded credentials remain
- Template syntax consistent across all files
- All spec references are valid
- All code tests pass: `pytest tests/ -x --tb=short`

---

## Phase 14: Spec Documentation — Remaining Contradictions

### Task T-040: Fix Remaining Spec Contradictions
**Issues**: #69, #102, #108
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/anchor-dataset/design.md` line 947 — add missing _transition_phase method definition
2. Read `specs/frontend-discovery-enhancement/requirements.md` — fix Type 3 LOGIC_ONLY language scope contradiction
3. Read `specs/module-discovery-auto/tasks.md` — fix overlapping line ranges (lines 285-478, 309-503, 334-528)
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-14

### Task T-041: Fix Additional Spec Issues
**Issues**: #109, #122, #68
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/module-discovery-auto/tasks.md.bak` — fix contradictory detection priority
2. Read `specs/prompt-externalization/plan.md` — resolve hardcoded vs YAML contradiction
3. Read `specs/anchor-dataset/design.md` — align retry exception scope across HTTP clients
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-14

### Task T-042: Fix Remaining Spec Issues
**Issues**: #57, #89, #91
**Priority**: P3 — spec correctness
**Do**:
1. Read `specs/_epics/aegf-infrastructure/epic.md` line 304 — fix langgraph version contradiction
2. Read `specs/dependency-compatibility/requirements.md` line 38 — fix langgraph pin syntax
3. Read `specs/dependency-compatibility/research.md` lines 269, 320 — fix langgraph version contradiction
**Verify**: `python -c "print('SPEC_DRY_RUN_OK')"` (doc-only changes)
**Quality Gate**: QG-14

---

## Quality Gate QG-14: Final Spec Fixes

**Party Mode Consensus Required** — all agents must approve:
- All spec contradictions resolved
- No overlapping task ranges
- Language scope clearly defined
- All code tests pass: `pytest tests/ -x --tb=short`

---

## Phase 15: Final Cleanups

### Task T-043: Fix Remaining Code Issues
**Issues**: #8, #27, #30, #32, #140
**Priority**: P3 — code quality
**Do**:
1. Read `infrastructure/dependency_check.py` — fix find_spec() exception handling (#8)
2. Read `infrastructure/anchor_dataset/startup.py` lines 34-41 — fix dry_run docstring contradiction (#27)
3. Read `infrastructure/anchor_dataset/anchor_providers.py` lines 282-283 — fix judge_scores AttributeError (#32)
4. Read `src/utils/extractors/extractors/i18n_key.py` lines 251-256 — fix unreliable _extract_template_prefix fallback (#140)
**Verify**: `python -m py_compile infrastructure/dependency_check.py infrastructure/anchor_dataset/startup.py && echo T-043_PASS`
**Quality Gate**: QG-15

### Task T-044: Fix Remaining Test Issues
**Issues**: #164, #165, #177, #184
**Priority**: P3 — test correctness
**Do**:
1. Read `tests/fixtures/reference_corpus/homeassistant/repo2/sensor.py` line 138 — fix wrong exception type for timeout (#164)
2. Read `tests/fixtures/reference_corpus/homeassistant/repo5/climate.py` line 95 — fix typo causing NameError (#165)
3. Read `tests/integration/test_ingestor_cli.py` line 180 — fix logical operator in assertion (#177)
4. Read `tests/test_nemo_pipeline_mocked.py` lines 100-101 — fix incorrect default value in getattr (#184)
**Verify**: `python -m py_compile tests/fixtures/reference_corpus/homeassistant/repo2/sensor.py tests/integration/test_ingestor_cli.py && echo T-044_PASS`
**Quality Gate**: QG-15

### Task T-045: Final Verification & Cleanup
**Issues**: All remaining Group 1 issues
**Priority**: P3 — final check
**Do**:
1. Run full test suite: `pytest tests/ -x --tb=short`
2. Run linter: `ruff check .`
3. Run syntax check: `find . -name '*.py' -exec python -m py_compile {} \;`
4. Run import check: `python -c "import infrastructure; import src"`
5. Verify no hardcoded credentials remain: `grep -r 'sk-master-bunker' . ; test $? -ne 0`
6. Verify all JSON valid: `find . -name '*.json' -exec python -c "import json; json.load(open('{}'))" \;`
7. Create summary of all fixes applied
**Verify**: `pytest tests/ -x --tb=short && ruff check . && echo T-045_PASS`
**Quality Gate**: QG-17

---

## Quality Gate QG-15: Code Quality Final

**Party Mode Consensus Required** — all agents must approve:
- All code compiles: `python -m py_compile` on every .py file
- All imports succeed
- `ruff check .` passes with zero errors
- All tests pass: `pytest tests/ -x --tb=short`
- No hardcoded credentials remain

---

## Quality Gate QG-16: Full Test Suite

**Party Mode Consensus Required** — all agents must approve:
- `pytest tests/ -v` — all tests pass
- No flaky tests
- No pragma cover
- Test names match assertions
- No dead code in tests
- All test fixtures are valid

---

## Quality Gate QG-17: Full Quality Check — FINAL

**Party Mode Consensus Required** — all agents must approve ALL checks:
1. **Syntax**: `python -m py_compile` on every .py file in the project
2. **Linter**: `ruff check .` passes with zero errors/warnings
3. **Imports**: `python -c "import infrastructure; import src; import tests"` succeeds
4. **Tests**: `pytest tests/ -v --tb=short` — ALL pass
5. **Coverage**: No pragma cover, no flaky tests, no dead code in tests
6. **Security**: No hardcoded credentials: `grep -r 'sk-master-bunker' . ; test $? -ne 0`
7. **JSON**: All JSON files valid: `find . -name '*.json' -exec python -c "import json; json.load(open('{}'))" \;`
8. **Spec Compliance**: All 102 issues from code-review-classification.md addressed
9. **Doc Consistency**: All spec contradictions resolved
10. **Code Quality**: No unused variables, no unreachable code, no dead branches

---

## Summary

| Metric | Count |
|--------|-------|
| Total Group 1 Issues | 102 |
| Total Tasks | 45 |
| Quality Gates | 17 |
| Issues per Task | ~2.3 average |

All quality gates require full party mode consensus before proceeding to next tasks.
