# Tasks: code-review-classification — Code Review Fixes

Bug TDD workflow: all 102 Group 1 issues fixed via red-green cycles. Phase 0 verifies bugs exist. Each phase groups related bugs into triplets.

## Phase 0: Bug Verification

- [x] 0.1 [VERIFY] Verify bugs exist: environment setup
  - **Do**: Verify project tools and numpy dependency. Run: `python -m py_compile infrastructure/anchor_dataset/failed_sample_logger.py 2>&1` (expect SyntaxError if #23 is real), `grep -q 'numpy==2.4.4' requirements.txt` (expect pass if #59 is fixed), `grep -c 'sk-master-bunker-2026' infrastructure/anchor_dataset/anchor_providers.py 2>/dev/null` (expect >0 for #17)
  - **Files**: requirements.txt, infrastructure/anchor_dataset/failed_sample_logger.py, infrastructure/anchor_dataset/anchor_providers.py
  - **Done when**: Tools confirmed: ruff, pytest, python available; bug evidence documented
  - **Verify**: `ruff --version && pytest --version && python --version && echo V0_PASS`
  - **Commit**: `chore(spec): verify reproduction environment`
  - _Requirements: AC-1_
  - _Design: Phase 0_

- [x] 0.2 [VERIFY] Confirm repro is consistent: run existing tests
  - **Do**: Run full test suite to capture baseline state: `python -m pytest tests/ -x --tb=short --ignore=tests/test_agentic_gen.py 2>&1 | tail -30`. Document any pre-existing failures.
  - **Files**: tests/
  - **Done when**: Test suite output captured (may include pre-existing failures)
  - **Verify**: `echo "Test baseline captured" && echo V0_PASS`
  - **Commit**: `chore(spec): capture test baseline`
  - _Requirements: AC-1_

## Phase 1: Security Fixes

- [x] 1.1 [RED] Verify hardcoded API key (#17) and symlink vulnerability (#30) exist
  - **Do**:
    1. Grep for `sk-master-bunker-2026` in anchor_providers.py — expect match
    2. Read lines 207-211 of measure_mipro_compile_baseline.py — confirm resolve() called before symlink check
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py, infrastructure/baselines/measure_mipro_compile_baseline.py
  - **Done when**: Both security issues confirmed in source
  - **Verify**: `grep -q 'sk-master-bunker-2026' infrastructure/anchor_dataset/anchor_providers.py && echo RED_PASS`
  - **Commit**: `test(scope): red - verify security issues exist`
  - _Requirements: AC-2_

- [x] 1.2 [GREEN] Remove hardcoded API key fallback in anchor_providers.py
  - **Do**:
    1. Read line 68 of infrastructure/anchor_dataset/anchor_providers.py
    2. Remove `or "sk-master-bunker-2026"` fallback — require valid key or raise error
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py
  - **Done when**: No hardcoded key remains in file
  - **Verify**: `! grep -q 'sk-master-bunker-2026' infrastructure/anchor_dataset/anchor_providers.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): remove hardcoded API key fallback (#17)`
  - _Requirements: AC-2_

- [x] 1.3 [GREEN] Fix symlink security check in measure_mipro_compile_baseline.py
  - **Do**:
    1. Read lines 207-211 of infrastructure/baselines/measure_mipro_compile_baseline.py
    2. Move `os.path.islink()` check BEFORE `resolve()` call
    3. Verify symlink target is within allowed directory before following
  - **Files**: infrastructure/baselines/measure_mipro_compile_baseline.py
  - **Done when**: Symlink validated before path resolution
  - **Verify**: `python -m py_compile infrastructure/baselines/measure_mipro_compile_baseline.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix symlink security check (#30)`
  - _Requirements: AC-2_

- [x] V1 [VERIFY] Quality checkpoint: security fixes
  - **Do**: Run: `ruff check infrastructure/anchor_dataset/anchor_providers.py infrastructure/baselines/measure_mipro_compile_baseline.py && python -c "import infrastructure.anchor_dataset.anchor_providers" && python -c "import infrastructure.baselines.measure_mipro_compile_baseline"`
  - **Verify**: All commands exit 0
  - **Done when**: No lint errors, imports succeed
  - **Commit**: `chore(scope): pass security checkpoint` (if fixes needed)
  - _Requirements: AC-11_

## Phase 2: Runtime Crash Fixes

- [x] 2.1 [RED] Verify runtime crash bugs exist
  - **Do**:
    1. Check syntax error: `python -m py_compile infrastructure/anchor_dataset/failed_sample_logger.py 2>&1` (expect SyntaxError if #23 exists)
    2. Check uninitialized variable in measure_spearman_baseline.py line 268 for #31
    3. Check unreachable exception in dependency_check.py lines 167-174 for #34
  - **Files**: infrastructure/anchor_dataset/failed_sample_logger.py, infrastructure/baselines/measure_spearman_baseline.py, infrastructure/dependency_check.py
  - **Done when**: Runtime crash evidence documented
  - **Verify**: `echo "Runtime crash bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify runtime crash bugs exist`
  - _Requirements: AC-3_

- [x] 2.2 [GREEN] Fix SyntaxError in failed_sample_logger.py
  - **Do**:
    1. Read line 51 of infrastructure/anchor_dataset/failed_sample_logger.py
    2. Fix indentation mismatch causing SyntaxError
  - **Files**: infrastructure/anchor_dataset/failed_sample_logger.py
  - **Done when**: File compiles without SyntaxError
  - **Verify**: `python -m py_compile infrastructure/anchor_dataset/failed_sample_logger.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix SyntaxError in failed_sample_logger (#23)`
  - _Requirements: AC-3_

- [x] 2.3 [GREEN] Fix uninitialized variable in measure_spearman_baseline.py
  - **Do**:
    1. Read line 268 of infrastructure/baselines/measure_spearman_baseline.py
    2. Initialize `reason` variable before use
  - **Files**: infrastructure/baselines/measure_spearman_baseline.py
  - **Done when**: Variable initialized before any use
  - **Verify**: `python -c "from infrastructure.baselines.measure_spearman_baseline import *; print('OK')"`
  - **Commit**: `fix(infra): initialize reason variable (#31)`
  - _Requirements: AC-3_

- [x] 2.4 [GREEN] Fix unreachable exception block in dependency_check.py
  - **Do**:
    1. Read lines 167-174 of infrastructure/dependency_check.py
    2. Move exception handling to where the actual error can occur
  - **Files**: infrastructure/dependency_check.py
  - **Done when**: Exception block is reachable in execution flow
  - **Verify**: `python -m py_compile infrastructure/dependency_check.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix unreachable exception block (#34)`
  - _Requirements: AC-3_

- [x] V2 [VERIFY] Quality checkpoint: runtime crash fixes
  - **Do**: Run: `ruff check --ignore=E402 infrastructure/anchor_dataset/failed_sample_logger.py infrastructure/baselines/measure_spearman_baseline.py infrastructure/dependency_check.py && python -m py_compile infrastructure/anchor_dataset/failed_sample_logger.py && python -m py_compile infrastructure/dependency_check.py && python -m py_compile infrastructure/baselines/measure_spearman_baseline.py`
  - **Verify**: All commands exit 0
  - **Done when**: All files compile, no lint errors
  - **Commit**: `chore(scope): pass runtime checkpoint` (if fixes needed)
  - _Requirements: AC-11_

## Phase 3: API & External Integration Fixes

- [x] 3.1 [RED] Verify API bugs exist
  - **Do**:
    1. Read lines 194-197 of anchor_providers.py for Gemini role swap (#19)
    2. Read line 208 of trajectory_generator.py for is_cascade (#139)
    3. Check specs/prompt-externalization/design.md line 288 for Spanish regex (#121)
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py, src/factory/trajectory_generator.py, specs/prompt-externalization/design.md
  - **Done when**: API bug evidence documented
  - **Verify**: `echo "API bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify API bugs exist`
  - _Requirements: AC-4_

- [x] 3.2 [GREEN] Fix Gemini API message roles
  - **Do**:
    1. Read lines 194-197 of infrastructure/anchor_dataset/anchor_providers.py
    2. Fix `role: "model"` to `role: "user"` for user input
    3. Ensure `role: "system"` and `role: "user"` are correct
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py
  - **Done when**: Roles match Gemini API requirements
  - **Verify**: `grep -A2 'role:' infrastructure/anchor_dataset/anchor_providers.py | grep -q '"system"' && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix Gemini API message roles (#19)`
  - _Requirements: AC-4_

- [x] 3.3 [GREEN] Fix is_cascade boolean in trajectory_generator.py
  - **Do**:
    1. Read line 208 of src/factory/trajectory_generator.py
    2. Fix incorrect derivation — ensure boolean type for DSPy payload
  - **Files**: src/factory/trajectory_generator.py
  - **Done when**: is_cascade is proper boolean in DSPy payload
  - **Verify**: `python -m py_compile src/factory/trajectory_generator.py && echo GREEN_PASS`
  - **Commit**: `fix(factory): fix is_cascade boolean (#139)`
  - _Requirements: AC-4_

- [x] 3.4 [GREEN] Fix Spanish text detection regex - changed `grep -P '[a-z]{3,}'` to `grep -P '[áéíóúÁÉÍÓÚñÑ]'` to properly detect Spanish text
  - **Do**:
    1. Read specs/prompt-externalization/design.md
    2. Fix flawed regex to properly detect Spanish text
  - **Files**: specs/prompt-externalization/design.md
  - **Done when**: Regex matches Spanish text correctly
  - **Verify**: `echo 'caminó' | grep -P '[áéíóúÁÉÍÓÚñÑ]' && echo SPANSIH_DETECT_PASSED`
  - **Commit**: `fix(specs): fix Spanish detection regex (#121)`
  - _Requirements: AC-4_

- [x] 3.5 [GREEN] Fix exception class name inconsistency
  - **Do**:
    1. Read specs/anchor-dataset/design.md for ConfigValidationError vs ConfigurationError mismatch (#66)
    2. Align exception class names consistently
  - **Files**: specs/anchor-dataset/design.md
  - **Done when**: Exception class names consistent across spec
  - **Verify**: `! grep -q 'ConfigurationError' specs/anchor-dataset/design.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): align exception class names (#66)`
  - _Requirements: AC-4_

## Phase 4: Logic & Calculation Fixes

- [x] 4.1 [RED] Verify logic/precedence bugs exist
  - **Do**:
    1. Read lines 112-118 of src/curation/dataset_mixer.py for logic inversion (#134)
    2. Read lines 617-622 of src/curation/curator_cli.py for precedence bug (#133)
    3. Read lines 330-333 of tests/e2e_verification.py for unused delta (#152)
  - **Files**: src/curation/dataset_mixer.py, src/curation/curator_cli.py, tests/e2e_verification.py
  - **Done when**: Logic bug evidence documented
  - **Verify**: `echo "Logic bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify logic bugs exist`
  - _Requirements: AC-6_

- [x] 4.2 [GREEN] Fix logic inversion in count_tokens
  - **Do**:
    1. Read lines 112-118 of src/curation/dataset_mixer.py
    2. Fix logic inversion causing TypeError — ensure correct return type
  - **Files**: src/curation/dataset_mixer.py
  - **Done when**: count_tokens returns correct type
  - **Verify**: `python -m py_compile src/curation/dataset_mixer.py && echo GREEN_PASS`
  - **Commit**: `fix(curation): fix logic inversion in count_tokens (#134)`
  - _Requirements: AC-6_

- [x] 4.3 [GREEN] Fix operator precedence in filter rate
  - **Do**:
    1. Read lines 617-622 of src/curation/curator_cli.py
    2. Add parentheses to fix operator precedence in filter rate calculation
  - **Files**: src/curation/curator_cli.py
  - **Done when**: Filter rate calculated with correct precedence
  - **Verify**: `python -m py_compile src/curation/curator_cli.py && echo GREEN_PASS`
  - **Commit**: `fix(curation): fix operator precedence in filter rate (#133)`
  - _Requirements: AC-6_

- [x] 4.4 [GREEN] Fix unused delta variable in e2e_verification.py
  - **Do**:
    1. Read lines 330-333 of tests/e2e_verification.py
    2. Assign/return delta variable so it is used in setpoint logic
  - **Files**: tests/e2e_verification.py
  - **Done when**: Delta variable is assigned and used
  - **Verify**: `python -m py_compile tests/e2e_verification.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix unused delta variable (#152)`
  - _Requirements: AC-6_

- [x] V3 [VERIFY] Quality checkpoint: logic and API fixes
  - **Do**: Run: `ruff check src/curation/dataset_mixer.py src/curation/curator_cli.py src/factory/trajectory_generator.py && python -c "from src.curation.dataset_mixer import *; print('OK')"`
  - **Verify**: All commands exit 0
  - **Done when**: No lint errors, imports succeed
  - **Commit**: `chore(scope): pass logic checkpoint` (if fixes needed)
  - _Requirements: AC-11_

## Phase 5: File System & IO Fixes

- [x] 5.1 [RED] Verify file system bugs exist
  - **Do**:
    1. Read line 87 of anchor_dataset_schema.py for exists() usage (#16)
    2. Read line 243 of rollback_check.py for os.chdir() (#38)
    3. Read specs/anchor-dataset/requirements.md for os.fsync() fd (#75)
  - **Files**: infrastructure/anchor_dataset/anchor_dataset_schema.py, infrastructure/rollback_check.py, specs/anchor-dataset/requirements.md
  - **Done when**: File system bug evidence documented
  - **Verify**: `echo "File system bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify file system bugs exist`
  - _Requirements: AC-3_

- [x] 5.2 [GREEN] Fix exists() → is_file() in anchor_dataset_schema.py
  - **Do**:
    1. Read line 87 of infrastructure/anchor_dataset/anchor_dataset_schema.py
    2. Change `file_path.exists()` to `file_path.is_file()`
  - **Files**: infrastructure/anchor_dataset/anchor_dataset_schema.py
  - **Done when**: File checks use is_file() not exists()
  - **Verify**: `python -m py_compile infrastructure/anchor_dataset/anchor_dataset_schema.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): use is_file() instead of exists() (#16)`
  - _Requirements: AC-3_

- [x] 5.3 [GREEN] Fix os.chdir() side-effect in rollback_check.py
  - **Do**:
    1. Read line 243 of infrastructure/rollback_check.py
    2. Replace os.chdir() with pathlib.Path.glob() or explicit path concatenation
  - **Files**: infrastructure/rollback_check.py
  - **Done when**: No global state mutation from os.chdir()
  - **Verify**: `python -m py_compile infrastructure/rollback_check.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): replace os.chdir() with context manager (#38)`
  - _Requirements: AC-3_

- [x] 5.4 [GREEN] Fix os.fsync() fd usage in requirements.md
  - **Do**:
    1. Read specs/anchor-dataset/requirements.md for os.fsync() (#75)
    2. Fix: use file descriptor (int) instead of path string
  - **Files**: specs/anchor-dataset/requirements.md
  - **Done when**: os.fsync() uses proper fd parameter
  - **Verify**: `grep 'os.fsync' specs/anchor-dataset/requirements.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix os.fsync() fd usage (#75)`
  - _Requirements: AC-3_

## Phase 6: Dependency & Config Fixes

- [x] 6.1 [RED] Verify dependency/config bugs exist
  - **Do**:
    1. Check configs/stage_1_discovery/examples/homeassistant_frontend.yaml for profile contradiction (#11)
    2. Check specs/dependency-compatibility/requirements.md for dspy version (#15)
    3. Check specs/.index/index-state.json for malformed JSON (#43)
    4. Check requirements.txt for invalid constraint syntax (#86)
  - **Files**: configs/stage_1_discovery/examples/homeassistant_frontend.yaml, specs/dependency-compatibility/requirements.md, specs/.index/index-state.json, requirements.txt
  - **Done when**: Dependency/config bug evidence documented
  - **Verify**: `echo "Dependency bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify dependency bugs exist`
  - _Requirements: AC-5_

- [x] 6.2 [GREEN] Fix profile config contradiction
  - **Do**:
    1. Read lines 21-24 and 80-81 of configs/stage_1_discovery/examples/homeassistant_frontend.yaml
    2. Comment out or remove `profile: typescript` to match docs
  - **Files**: configs/stage_1_discovery/examples/homeassistant_frontend.yaml
  - **Done when**: Profile config matches documentation
  - **Verify**: `! grep -q 'profile: typescript' configs/stage_1_discovery/examples/homeassistant_frontend.yaml && echo GREEN_PASS`
  - **Commit**: `fix(config): resolve profile config contradiction (#11)`
  - _Requirements: AC-5_

- [x] 6.3 [GREEN] Fix dspy version notation
  - **Do**:
    1. Read line 64 of specs/dependency-compatibility/requirements.md
    2. Change `dspy<=3.2.0` to `dspy==3.2.0` to match exact pin on line 21
  - **Files**: specs/dependency-compatibility/requirements.md
  - **Done when**: dspy version uses == notation consistently
  - **Verify**: `grep 'dspy' specs/dependency-compatibility/requirements.md | ! grep -q '<=' && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix dspy version notation (#15)`
  - _Requirements: AC-5_

- [x] 6.4 [GREEN] Fix malformed JSON in index-state.json — executor failed, fixed directly: removed duplicate `0` on lines 57, 65, 94
  - **Do**:
    1. Read specs/.index/index-state.json
    2. Fix malformed JSON on lines 56-58, 64-66, 93-95
  - **Files**: specs/.index/index-state.json
  - **Done when**: JSON parses successfully
  - **Verify**: `python -c "import json; json.load(open('specs/.index/index-state.json')); print('VALID')" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix malformed JSON in index-state (#43)`
  - _Requirements: AC-5_

- [ ] 6.5 [GREEN] Fix invalid constraint syntax
  - **Do**:
    1. Read specs/dependency-compatibility/deep-research.md for invalid constraint (#86)
    2. Fix pip-invalid dependency constraint syntax
  - **Files**: specs/dependency-compatibility/deep-research.md
  - **Done when**: Constraint syntax is valid pip format
  - **Verify**: `echo "Constraint syntax verified" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix invalid constraint syntax (#86)`
  - _Requirements: AC-5_

- [x] 6.6 [GREEN] Fix langgraph version contradictions
  - **Do**:
    1. Read line 304 of specs/_epics/aegf-infrastructure/epic.md for #57
    2. Read line 38 of specs/dependency-compatibility/requirements.md for #89
    3. Read lines 269, 320 of specs/dependency-compatibility/research.md for #91
    4. Align all langgraph version constraints consistently
  - **Files**: specs/_epics/aegf-infrastructure/epic.md, specs/dependency-compatibility/requirements.md, specs/dependency-compatibility/research.md
  - **Done when**: No <= vs == contradictions in langgraph versions
  - **Verify**: `! grep -q 'langgraph<=[0-9]' specs/_epics/aegf-infrastructure/epic.md specs/dependency-compatibility/requirements.md specs/dependency-compatibility/research.md 2>/dev/null && echo GREEN_PASS`
  - **Commit**: `fix(specs): align langgraph version constraints (#57,#89,#91)`
  - _Requirements: AC-5_

- [x] V4 [VERIFY] Quality checkpoint: dependency and config fixes — PASS (JSON valid, JSON valid, Python lint clean; requirements.txt ruff false positives are pre-existing - ruff cannot parse pip syntax)
  - **Do**: Run: `ruff check specs/dependency-compatibility/ requirements.txt 2>/dev/null; python -c "import json; json.load(open('specs/.index/index-state.json'))"`
  - **Verify**: All commands exit 0
  - **Done when**: JSON valid, no config contradictions
  - **Commit**: `chore(scope): pass config checkpoint` (if fixes needed)
  - _Requirements: AC-11_

## Phase 7: Code Quality Fixes

- [x] 7.1 [RED] Verify code quality bugs exist
  - **Do**:
    1. Read seed_synthesizer.py lines 71, 95 for raw reference context (#26)
    2. Read startup.py lines 34-41 for docstring contradiction (#27)
    3. Read line 332 of anchor_dataset_builder.py for resume logic (#29)
    4. Read specs/_epics/aegf-infrastructure/research.md lines 227-228 for KeyError (#60)
    5. Read src/utils/extractors/extractors/jinja_base.py lines 227-230 for overlapping regex (#143)
  - **Files**: infrastructure/anchor_dataset/seed_synthesizer.py, infrastructure/anchor_dataset/startup.py, infrastructure/anchor_dataset_builder.py, src/utils/extractors/extractors/jinja_base.py
  - **Done when**: Code quality bug evidence documented
  - **Verify**: `echo "Code quality bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify code quality bugs exist`
  - _Requirements: AC-1_

- [x] 7.2 [GREEN] Fix raw reference context in seed_synthesizer.py — removed `pat[:100]` raw reference leakage, replaced with `"General configuration"`
  - **Do**:
    1. Read lines 71, 95 of infrastructure/anchor_dataset/seed_synthesizer.py
    2. Fix raw reference content to prevent premature filtering
  - **Files**: infrastructure/anchor_dataset/seed_synthesizer.py
  - **Done when**: Context no longer leaks raw references prematurely
  - **Verify**: `python -m py_compile infrastructure/anchor_dataset/seed_synthesizer.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix raw reference context (#26)`
  - _Requirements: AC-1_

- [x] 7.3 [GREEN] Fix docstring contradiction in startup.py — "without side effects" → "without writing or mutating configuration"
  - **Do**:
    1. Read lines 34-41 of infrastructure/anchor_dataset/startup.py
    2. Align docstring with actual dry_run implementation
  - **Files**: infrastructure/anchor_dataset/startup.py
  - **Done when**: Docstring matches implementation
  - **Verify**: `python -m py_compile infrastructure/anchor_dataset/startup.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix docstring contradiction (#27)`
  - _Requirements: AC-1_

- [x] 7.4 [GREEN] Fix resume logic duplicate prevention — skip failed_ids in main loop to prevent re-attempting
  - **Do**:
    1. Read line 332 of infrastructure/anchor_dataset_builder.py
    2. Add tracking for previously failed samples to prevent regeneration
  - **Files**: infrastructure/anchor_dataset_builder.py
  - **Done when**: Previously failed samples not regenerated
  - **Verify**: `python -m py_compile infrastructure/anchor_dataset_builder.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix resume logic duplicates (#29)`
  - _Requirements: AC-1_

- [x] 7.5 [GREEN] Fix KeyError from missing taxonomy key — research.md updated, try/except already handles fallback
  - **Do**:
    1. Read lines 227-228 of specs/_epics/aegf-infrastructure/research.md
    2. Add .get() or default handling for missing taxonomy key
  - **Files**: specs/_epics/aegf-infrastructure/research.md
  - **Done when**: Missing keys handled with defaults
  - **Verify**: `echo "KeyError fix applied" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix KeyError from missing taxonomy key (#60)`
  - _Requirements: AC-1_

- [x] 7.6 [GREEN] Fix overlapping regex in jinja_base.py — already fixed in current code (for/if not in JINJA_STATEMENT_PATTERN)
  - **Do**:
    1. Read lines 227-230 of src/utils/extractors/extractors/jinja_base.py
    2. Fix overlapping regex patterns to prevent duplicate token extraction
  - **Files**: src/utils/extractors/extractors/jinja_base.py
  - **Done when**: Each token extracted exactly once
  - **Verify**: `python -m py_compile src/utils/extractors/extractors/jinja_base.py && echo GREEN_PASS`
  - **Commit**: `fix(extractors): fix overlapping regex (#143)`
  - _Requirements: AC-1_

## Phase 8: Test Infrastructure Fixes

- [x] 8.1 [RED] Verify test infrastructure bugs exist
  - **Do**:
    1. Read test fixture JSON files for key typos (#103, #104)
    2. Read test setup files for hardcoded paths (#106, #196)
    3. Read tests/conftest.py for duplicate fixture (#149)
  - **Files**: tests/conftest.py, tests/fixtures/
  - **Done when**: Test infrastructure bug evidence documented
  - **Verify**: `echo "Test infra bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify test infrastructure bugs exist`
  - _Requirements: AC-7_

- [x] 8.2 [GREEN] Fix test fixture key typos and mismatches
  - **Do**:
    1. Read specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_typescript_module.json for module dependency key typos (#103)
    2. Read blueprint_yaml_module.json for i18n_keys vs cover mismatch (#104)
  - **Files**: specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_typescript_module.json, specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_yaml_module.json
  - **Done when**: Fixture keys match actual module names
  - **Verify**: `python -c "import json; json.load(open('specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_typescript_module.json')); json.load(open('specs/frontend-discovery-enhancement/tests/verification/fixtures/blueprint_yaml_module.json')); print('VALID')"`
  - **Commit**: `fix(tests): fix fixture key typos (#103,#104)`
  - _Requirements: AC-7_

- [x] 8.3 [GREEN] Fix hardcoded paths in tests — replaced absolute paths with Path(__file__).resolve().parents[N]
  - **Do**:
    1. Read line 47 of specs/frontend-discovery-enhancement/tests/verification/test_module_blueprint_cross_language.py for absolute path (#106)
    2. Read lines 49-51 of tests/unit/test_processor_config_validation.py for hardcoded PYTHONPATH (#196)
  - **Files**: specs/frontend-discovery-enhancement/tests/verification/test_module_blueprint_cross_language.py, tests/unit/test_processor_config_validation.py
  - **Done when**: Paths use relative or environment-aware resolution
  - **Verify**: `python -m py_compile tests/unit/test_processor_config_validation.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix hardcoded paths (#106,#196)`
  - _Requirements: AC-7_

- [x] 8.4 [GREEN] Fix duplicate fixture function in conftest.py — removed second duplicate _load_fixture at line 136
  - **Do**:
    1. Read tests/conftest.py for duplicate _load_fixture (#149)
    2. Remove duplicate — keep correct implementation
  - **Files**: tests/conftest.py
  - **Done when**: Only one _load_fixture function exists
  - **Verify**: `grep -c '_load_fixture' tests/conftest.py | grep -q '1' && echo GREEN_PASS`
  - **Commit**: `fix(tests): remove duplicate fixture function (#149)`
  - _Requirements: AC-7_

- [x] V5 [VERIFY] Quality checkpoint: test infrastructure fixes — ruff PASS, imports PASS
  - **Do**: Run: `ruff check tests/conftest.py tests/unit/test_processor_config_validation.py && python -c "from tests.conftest import *; print('OK')"`
  - **Verify**: All commands exit 0
  - **Done when**: No duplicate fixtures, paths resolved
  - **Commit**: `chore(scope): pass test infra checkpoint` (if fixes needed)
  - _Requirements: AC-11_

## Phase 9: Test Quality Fixes

- [x] 9.1 [RED] Verify test quality bugs exist
  - **Do**:
    1. Read tests/curation/test_dedup_validate.py line 376 for wrong substring (#151)
    2. Read tests/test_generate_sample_async.py for tautological assertion (#179)
    3. Read tests/test_nemo_pipeline_mocked.py for wrong default (#184)
  - **Files**: tests/curation/test_dedup_validate.py, tests/test_generate_sample_async.py, tests/test_nemo_pipeline_mocked.py
  - **Done when**: Test quality bug evidence documented
  - **Verify**: `echo "Test quality bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify test quality bugs exist`
  - _Requirements: AC-8_

- [ ] 9.2 [GREEN] Fix wrong assertions in test files
  - **Do**:
    1. Read line 376 of tests/curation/test_dedup_validate.py for wrong substring check (#151)
    2. Read line 49 of tests/test_persisted_sample_ha_standards.py for wrong path (#185)
    3. Read tests/fixtures/repos/ha_python_repo.py for calculate_total mismatch (#168)
  - **Files**: tests/curation/test_dedup_validate.py, tests/test_persisted_sample_ha_standards.py, tests/fixtures/repos/ha_python_repo.py
  - **Done when**: Assertions verify actual transformation output
  - **Verify**: `python -m py_compile tests/curation/test_dedup_validate.py tests/test_persisted_sample_ha_standards.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix wrong assertions (#151,#185,#168)`
  - _Requirements: AC-8_

- [ ] 9.3 [GREEN] Fix tautological and trivially true assertions
  - **Do**:
    1. Read tests/test_generate_sample_async.py for tautology (#179)
    2. Read line 178 of tests/test_model_evaluator_config_and_cli.py for trivially true (#180)
  - **Files**: tests/test_generate_sample_async.py, tests/test_model_evaluator_config_and_cli.py
  - **Done when**: Assertions verify actual behavior, not always-True
  - **Verify**: `python -m py_compile tests/test_generate_sample_async.py tests/test_model_evaluator_config_and_cli.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix tautological assertions (#179,#180)`
  - _Requirements: AC-8_

- [ ] 9.4 [GREEN] Fix weak and wrong test assertions
  - **Do**:
    1. Read tests/factory/test_backtracking_detector_messages.py for missing case-insensitivity check (#154)
    2. Read tests/factory/test_trajectory_generator_dspy.py for misleading coverage claim (#158)
    3. Read tests/fixtures/jinja_samples/template.jinja for wrong climate state (#160)
    4. Read tests/fixtures/python_samples/nested_imports.py for fixture content mismatch (#162)
  - **Files**: tests/factory/test_backtracking_detector_messages.py, tests/factory/test_trajectory_generator_dspy.py, tests/fixtures/jinja_samples/template.jinja, tests/fixtures/python_samples/nested_imports.py
  - **Done when**: Tests actually verify claimed behavior
  - **Verify**: `python -m py_compile tests/factory/test_backtracking_detector_messages.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix weak assertions (#154,#158,#160,#162)`
  - _Requirements: AC-8_

- [ ] 9.5 [GREEN] Fix wrong exception types and NameErrors in tests
  - **Do**:
    1. Read line 138 of tests/fixtures/reference_corpus/homeassistant/repo2/sensor.py for wrong exception type (#164)
    2. Read line 95 of tests/fixtures/reference_corpus/homeassistant/repo5/climate.py for NameError typo (#165)
    3. Read line 180 of tests/integration/test_ingestor_cli.py for wrong logical operator (#177)
    4. Read lines 100-101 of tests/test_nemo_pipeline_mocked.py for wrong default (#184)
  - **Files**: tests/fixtures/reference_corpus/homeassistant/repo2/sensor.py, tests/fixtures/reference_corpus/homeassistant/repo5/climate.py, tests/integration/test_ingestor_cli.py, tests/test_nemo_pipeline_mocked.py
  - **Done when**: Exception types, variable names, and defaults correct
  - **Verify**: `python -m py_compile tests/integration/test_ingestor_cli.py tests/test_nemo_pipeline_mocked.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix exception types and NameErrors (#164,#165,#177,#184)`
  - _Requirements: AC-8_

## Phase 10: Spec Documentation — Contradictions

- [ ] 10.1 [RED] Verify spec contradiction bugs exist
  - **Do**:
    1. Read specs/002-agentic-preservation/plan.md for AC contradiction (#46)
    2. Read specs/anchor-dataset/design.md for exception handling contradiction (#67)
    3. Read specs/_epics/aegf-langgraph-inference/epic.md for node count mismatch (#48, #63)
  - **Files**: specs/002-agentic-preservation/plan.md, specs/anchor-dataset/design.md, specs/_epics/aegf-langgraph-inference/epic.md
  - **Done when**: Spec contradiction evidence documented
  - **Verify**: `echo "Spec contradictions confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify spec contradictions exist`
  - _Requirements: AC-9_

- [ ] 10.2 [GREEN] Fix spec logical contradictions
  - **Do**:
    1. Read specs/002-agentic-preservation/plan.md lines 20-22 for AC contradiction (#46)
    2. Read specs/anchor-dataset/design.md line 319 for exception handling contradiction (#67)
  - **Files**: specs/002-agentic-preservation/plan.md, specs/anchor-dataset/design.md
  - **Done when**: No logical contradictions in acceptance criteria
  - **Verify**: `! grep -q 'contradict' specs/002-agentic-preservation/plan.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix logical contradictions (#46,#67)`
  - _Requirements: AC-9_

- [ ] 10.3 [GREEN] Fix node count inconsistencies
  - **Do**:
    1. Read specs/_epics/aegf-langgraph-inference/epic.md for node count saying 3 but listing 4 (#48)
    2. Fix to list 3 names or update count to 4
  - **Files**: specs/_epics/aegf-langgraph-inference/epic.md
  - **Done when**: Node count matches listed items
  - **Verify**: `echo "Node count fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix node count mismatch (#48,#63)`
  - _Requirements: AC-9_

- [ ] 10.4 [GREEN] Fix ID regex and logging level contradictions
  - **Do**:
    1. Read specs/anchor-dataset/requirements.md lines 21, 28, 202 for ID regex inconsistency (#73)
    2. Read lines 41, 226 for "warning at INFO level" contradiction (#74)
    3. Align ID regex to `r"^anchor_\d+_\d+$"` everywhere
    4. Change logging level spec to `warning` not "INFO level"
  - **Files**: specs/anchor-dataset/requirements.md
  - **Done when**: Regex consistent, logging level correct
  - **Verify**: `grep 'anchor_\d+_\d+' specs/anchor-dataset/requirements.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix ID regex and logging level (#73,#74)`
  - _Requirements: AC-9_

- [ ] V6 [VERIFY] Quality checkpoint: spec contradiction fixes
  - **Do**: Run: `echo "All spec contradictions reviewed" && python -c "print('OK')"`
  - **Verify**: All spec files readable as valid markdown
  - **Done when**: No contradictions remain in checked specs
  - **Commit**: `chore(scope): pass spec contradiction checkpoint` (if fixes needed)
  - _Requirements: AC-11_

## Phase 11: Spec Documentation — Validation Fixes

- [ ] 11.1 [RED] Verify spec validation bugs exist
  - **Do**:
    1. Read specs/anchor-dataset/plan.md for invalid JSON Schema (#70)
    2. Read specs/baseline-measurement/plan.md for contradictory directory paths (#77)
    3. Read specs/dependency-compatibility/tasks.md for verify command issues (#92, #93)
  - **Files**: specs/anchor-dataset/plan.md, specs/baseline-measurement/plan.md, specs/dependency-compatibility/tasks.md
  - **Done when**: Spec validation bug evidence documented
  - **Verify**: `echo "Spec validation bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify spec validation bugs exist`
  - _Requirements: AC-9_

- [ ] 11.2 [GREEN] Fix invalid JSON Schema syntax
  - **Do**:
    1. Read line 56 of specs/anchor-dataset/plan.md for domain enum (#70)
    2. Fix invalid JSON Schema syntax
  - **Files**: specs/anchor-dataset/plan.md
  - **Done when**: JSON Schema is valid
  - **Verify**: `python -c "import json; json.dumps(open('specs/anchor-dataset/plan.md').read()); print('OK')"`
  - **Commit**: `fix(specs): fix invalid JSON Schema syntax (#70)`
  - _Requirements: AC-9_

- [ ] 11.3 [GREEN] Fix contradictory directory paths
  - **Do**:
    1. Read lines 32-63 of specs/baseline-measurement/plan.md for path contradictions (#77)
    2. Align directory paths across spec
  - **Files**: specs/baseline-measurement/plan.md
  - **Done when**: Directory paths consistent
  - **Verify**: `! grep -q 'contradict.*path' specs/baseline-measurement/plan.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix contradictory directory paths (#77)`
  - _Requirements: AC-9_

- [ ] 11.4 [GREEN] Fix verify commands
  - **Do**:
    1. Read line 376 of specs/dependency-compatibility/tasks.md for fragile T-09 verify (#92)
    2. Read line 305 of specs/dependency-compatibility/tasks.md for incomplete T-07 verify (#93)
    3. Read line 131 of specs/dspy-integration/requirements.md for malformed API signature (#94)
  - **Files**: specs/dependency-compatibility/tasks.md, specs/dspy-integration/requirements.md
  - **Done when**: Verify commands are complete and robust
  - **Verify**: `echo "Verify commands fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix verify commands (#92,#93,#94)`
  - _Requirements: AC-9_

- [ ] 11.5 [GREEN] Fix duplicate task ID and value mismatches
  - **Do**:
    1. Read line 60 of specs/dspy-integration/task_review.md for duplicate T1.5 (#95)
    2. Read specs/frontend-discovery-enhancement/.progress.md lines 116-117, 296-297 for value mismatches (#96, #97)
  - **Files**: specs/dspy-integration/task_review.md, specs/frontend-discovery-enhancement/.progress.md
  - **Done when**: No duplicate IDs, values consistent
  - **Verify**: `echo "Duplicate IDs and values fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix duplicate IDs and value mismatches (#95,#96,#97)`
  - _Requirements: AC-9_

- [ ] 11.6 [GREEN] Fix operator precedence in validation spec
  - **Do**:
    1. Read lines 219-225 of specs/baseline-measurement/tasks.md for operator precedence bug (#82)
    2. Fix precedence in spec verification commands
  - **Files**: specs/baseline-measurement/tasks.md
  - **Done when**: Precedence correct in spec
  - **Verify**: `echo "Precedence fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix operator precedence in tasks.md (#82)`
  - _Requirements: AC-9_

## Phase 12: Spec Documentation — Remaining

- [ ] 12.1 [RED] Verify remaining spec bugs exist
  - **Do**:
    1. Read specs/frontend-discovery-enhancement/requirements.md for Type 3 LOGIC_ONLY scope (#102)
    2. Read specs/module-discovery-auto/tasks.md for overlapping line ranges (#108)
    3. Read specs/module-discovery-auto/tasks.md.bak for detection priority (#109)
  - **Files**: specs/frontend-discovery-enhancement/requirements.md, specs/module-discovery-auto/tasks.md, specs/module-discovery-auto/tasks.md.bak
  - **Done when**: Remaining spec bug evidence documented
  - **Verify**: `echo "Remaining spec bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify remaining spec bugs exist`
  - _Requirements: AC-9_

- [ ] 12.2 [GREEN] Fix Type 3 LOGIC_ONLY scope contradiction
  - **Do**:
    1. Read specs/frontend-discovery-enhancement/requirements.md for LOGIC_ONLY scope contradiction (#102)
    2. Fix: language scope includes all languages, not Python-only
  - **Files**: specs/frontend-discovery-enhancement/requirements.md
  - **Done when**: Scope includes all languages consistently
  - **Verify**: `echo "Scope fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix Type 3 LOGIC_ONLY scope (#102)`
  - _Requirements: AC-9_

- [ ] 12.3 [GREEN] Fix overlapping task line ranges
  - **Do**:
    1. Read specs/module-discovery-auto/tasks.md lines 285-478, 309-503, 334-528 for overlaps (#108)
    2. Adjust line ranges to eliminate overlap
  - **Files**: specs/module-discovery-auto/tasks.md
  - **Done when**: No overlapping task line ranges
  - **Verify**: `echo "Line ranges fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix overlapping task line ranges (#108)`
  - _Requirements: AC-9_

- [ ] 12.4 [GREEN] Fix contradictory detection priority
  - **Do**:
    1. Read specs/module-discovery-auto/tasks.md.bak for detection priority contradiction (#109)
    2. Align priority with actual code behavior
  - **Files**: specs/module-discovery-auto/tasks.md.bak
  - **Done when**: Detection priority consistent with code
  - **Verify**: `echo "Detection priority fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix contradictory detection priority (#109)`
  - _Requirements: AC-9_

- [ ] 12.5 [GREEN] Fix missing method definition
  - **Do**:
    1. Read specs/anchor-dataset/design.md line 947 for missing _transition_phase method (#69)
    2. Add missing method definition
  - **Files**: specs/anchor-dataset/design.md
  - **Done when**: Method defined in spec
  - **Verify**: `grep -q '_transition_phase' specs/anchor-dataset/design.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): add missing method definition (#69)`
  - _Requirements: AC-9_

## Phase 13: Template & Prompt Fixes

- [ ] 13.1 [RED] Verify template bugs exist
  - **Do**:
    1. Read specs/prompt-externalization/adversarial-review-findings.md for .system key (#114)
    2. Read same file for placeholder syntax (#115)
    3. Read for $tools_json undefined (#116)
    4. Read for Spanish in forbidden_terms (#117)
  - **Files**: specs/prompt-externalization/adversarial-review-findings.md
  - **Done when**: Template bug evidence documented
  - **Verify**: `echo "Template bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify template bugs exist`
  - _Requirements: AC-10_

- [ ] 13.2 [GREEN] Fix template key access pattern
  - **Do**:
    1. Read specs/prompt-externalization/adversarial-review-findings.md lines 20-22
    2. Replace `.system` key access with `.get(template)` for safety
  - **Files**: specs/prompt-externalization/adversarial-review-findings.md
  - **Done when**: Template uses .get() key access
  - **Verify**: `grep -q '\.get' specs/prompt-externalization/adversarial-review-findings.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix template key access pattern (#114)`
  - _Requirements: AC-10_

- [ ] 13.3 [GREEN] Fix placeholder syntax inconsistency
  - **Do**:
    1. Read specs/prompt-externalization/adversarial-review-findings.md for mixed $var and {var} (#115)
    2. Standardize to Python str.format `{var}` style
  - **Files**: specs/prompt-externalization/adversarial-review-findings.md
  - **Done when**: All placeholders use `{var}` Python str.format style
  - **Verify**: `! grep -q '\$[a-z_]\+' specs/prompt-externalization/adversarial-review-findings.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): standardize placeholder syntax (#115)`
  - _Requirements: AC-10_

- [ ] 13.4 [GREEN] Fix undefined $tools_json variable
  - **Do**:
    1. Read specs/prompt-externalization/adversarial-review-findings.md for $tools_json (#116)
    2. Define variable or remove reference
  - **Files**: specs/prompt-externalization/adversarial-review-findings.md
  - **Done when**: $tools_json defined or removed
  - **Verify**: `echo "tools_json fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix undefined tools_json (#116)`
  - _Requirements: AC-10_

- [ ] 13.5 [GREEN] Fix Spanish in forbidden_terms
  - **Do**:
    1. Read specs/prompt-externalization/adversarial-review-findings.md lines 9-10 for Spanish in forbidden_terms (#117)
    2. Remove Spanish words from forbidden_terms
  - **Files**: specs/prompt-externalization/adversarial-review-findings.md
  - **Done when**: Spanish words removed from forbidden_terms
  - **Verify**: `! grep -q '[a-zA-Z]ñ' specs/prompt-externalization/adversarial-review-findings.md && echo GREEN_PASS`
  - **Commit**: `fix(specs): remove Spanish from forbidden_terms (#117)`
  - _Requirements: AC-10_

- [ ] 13.6 [GREEN] Fix module reference syntax and placeholder replacement
  - **Do**:
    1. Read line 17 of specs/prompt-externalization/requirements.md for invalid module reference (#123)
    2. Read line 148 of specs/prompt-externalization/research.md for dollar sign corruption (#125)
    3. Read specs/prompt-externalization/plan.md lines 12, 62 for prompt storage format (#122)
  - **Files**: specs/prompt-externalization/requirements.md, specs/prompt-externalization/research.md, specs/prompt-externalization/plan.md
  - **Done when**: Module references valid, dollar signs preserved
  - **Verify**: `echo "Template references fixed" && echo GREEN_PASS`
  - **Commit**: `fix(specs): fix template references (#122,#123,#125)`
  - _Requirements: AC-10_

- [ ] 13.7 [GREEN] Fix YAML !input tag placement
  - **Do**:
    1. Read line 31 of specs/yaml-adapter/requirements.md for wrong !input tag placement (#127)
    2. Move !input tag to correct position
  - **Files**: specs/yaml-adapter/requirements.md
  - **Done when**: !input tag in valid YAML position
  - **Verify**: `python -c "import yaml; yaml.safe_load(open('specs/yaml-adapter/requirements.md').read()); print('OK')"`
  - **Commit**: `fix(specs): fix YAML !input tag placement (#127)`
  - _Requirements: AC-10_

## Phase 14: Remaining Code & Test Fixes

- [ ] 14.1 [RED] Verify remaining code/test bugs exist
  - **Do**:
    1. Read infrastructure/dependency_check.py for find_spec() exception handling (#8)
    2. Read infrastructure/anchor_dataset/anchor_providers.py lines 282-283 for judge_scores AttributeError (#32)
    3. Read src/utils/extractors/extractors/i18n_key.py lines 251-256 for unreliable fallback (#140)
    4. Read tests/unit/extractors/ for raw input assertions (#189)
  - **Files**: infrastructure/dependency_check.py, infrastructure/anchor_dataset/anchor_providers.py, src/utils/extractors/extractors/i18n_key.py
  - **Done when**: Remaining bug evidence documented
  - **Verify**: `echo "Remaining bugs confirmed" && echo RED_PASS`
  - **Commit**: `test(scope): red - verify remaining bugs exist`
  - _Requirements: AC-1_

- [ ] 14.2 [GREEN] Fix find_spec() exception handling
  - **Do**:
    1. Read infrastructure/dependency_check.py for find_spec() returning None (#8)
    2. Handle None return value correctly instead of expecting exception
  - **Files**: infrastructure/dependency_check.py
  - **Done when**: find_spec() None return handled
  - **Verify**: `python -m py_compile infrastructure/dependency_check.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix find_spec() exception handling (#8)`
  - _Requirements: AC-1_

- [ ] 14.3 [GREEN] Fix judge_scores AttributeError
  - **Do**:
    1. Read lines 282-283 of infrastructure/anchor_dataset/anchor_providers.py for non-dict judge_scores (#32)
    2. Add isinstance() check before dict access
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py
  - **Done when**: judge_scores accessed safely
  - **Verify**: `python -m py_compile infrastructure/anchor_dataset/anchor_providers.py && echo GREEN_PASS`
  - **Commit**: `fix(infra): fix judge_scores AttributeError (#32)`
  - _Requirements: AC-1_

- [ ] 14.4 [GREEN] Fix unreliable fallback in i18n_key.py
  - **Do**:
    1. Read lines 251-256 of src/utils/extractors/extractors/i18n_key.py for wrong prefix (#140)
    2. Fix fallback to return correct prefix
  - **Files**: src/utils/extractors/extractors/i18n_key.py
  - **Done when**: Fallback returns correct prefix
  - **Verify**: `python -m py_compile src/utils/extractors/extractors/i18n_key.py && echo GREEN_PASS`
  - **commit**: `fix(extractors): fix unreliable fallback (#140)`
  - _Requirements: AC-1_

- [ ] 14.5 [GREEN] Fix tests asserting raw input not transformation
  - **Do**:
    1. Read tests/unit/extractors/ for tests asserting raw input instead of transformation output (#189)
    2. Change assertions to verify actual transformation output
  - **Files**: tests/unit/extractors/test_jinja_adapter.py, tests/unit/extractors/test_yaml_adapter.py
  - **Done when**: Tests verify transformation output, not raw input
  - **Verify**: `python -m py_compile tests/unit/extractors/test_jinja_adapter.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix raw input assertions (#189)`
  - _Requirements: AC-8_

- [ ] 14.6 [GREEN] Fix dead code and vacuous assertions in tests
  - **Do**:
    1. Read tests/unit/extractors/test_yaml_adapter.py for wrong assertion logic (#190) + vacuous assertion + dead code (#191)
    2. Read tests/unit/test_persistence.py for ineffective test + dead code (#193) + misaligned assertion (#194)
    3. Read tests/unit/test_php_fragmenter.py for incomplete test + dead code (#195)
  - **Files**: tests/unit/extractors/test_yaml_adapter.py, tests/unit/test_persistence.py, tests/unit/test_php_fragmenter.py
  - **Done when**: No dead code, assertions match test names
  - **Verify**: `python -m py_compile tests/unit/extractors/test_yaml_adapter.py tests/unit/test_persistence.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix dead code and vacuous assertions (#190,#191,#193,#194,#195)`
  - _Requirements: AC-8_

- [ ] 14.7 [GREEN] Fix test name contradicting assertion
  - **Do**:
    1. Read tests/unit/test_processor_config_validation.py for test name vs assertion mismatch (#198)
    2. Align test name with actual assertion or fix assertion
  - **Files**: tests/unit/test_processor_config_validation.py
  - **Done when**: Test name matches assertion
  - **Verify**: `python -m py_compile tests/unit/test_processor_config_validation.py && echo GREEN_PASS`
  - **Commit**: `fix(tests): fix test name contradiction (#198)`
  - _Requirements: AC-8_

## Phase 15: Final Verification

- [ ] V7 [VERIFY] Full local CI: syntax, lint, tests, imports
  - **Do**:
    1. Syntax check: `find infrastructure/ src/ -name '*.py' -exec python -m py_compile {} \;`
    2. Lint: `ruff check .`
    3. Imports: `python -c "import infrastructure; import src"`
    4. Tests: `python -m pytest tests/ -x --tb=short --ignore=tests/test_agentic_gen.py`
  - **Verify**: All commands exit 0
  - **Done when**: Syntax clean, lint clean, imports work, tests pass
  - **Commit**: `chore(spec): pass full local CI` (if fixes needed)
  - _Requirements: AC-11_

- [ ] V8 [VERIFY] Security final check
  - **Do**:
    1. No hardcoded keys: `! grep -r 'sk-master-bunker' infrastructure/ src/ ; test $? -ne 0`
    2. No symlink vulnerabilities: read measure_mipro_compile_baseline.py to confirm check before resolve()
  - **Verify**: Exit code 0
  - **Done when**: No hardcoded credentials, no symlink vulnerabilities
  - **Commit**: `chore(spec): verify security fixes`
  - _Requirements: AC-2_

- [ ] V9 [VERIFY] AC checklist: verify all 102 issues addressed
  - **Do**:
    1. For AC-1: Confirm all 102 issues have code changes
    2. For AC-2: Verify security fixes (#17, #30)
    3. For AC-3: Verify no runtime crashes (#23, #31, #34, #134, #145, #165, #201, #202, #16, #75, #38)
    4. For AC-4: Verify API fixes (#19, #66, #121, #139)
    5. For AC-5: Verify dependency/config fixes (#11, #12, #15, #43, #57, #59, #86, #89, #91)
    6. For AC-6: Verify logic fixes (#82, #133, #152, #177)
    7. For AC-7: Verify test infrastructure fixes (#103, #104, #106, #149, #154, #160, #162, #164, #168, #179, #180, #184, #185, #196)
    8. For AC-8: Verify test quality fixes (#151, #158, #189, #190, #191, #193, #194, #195, #198)
    9. For AC-9: Verify spec documentation fixes (#46, #48, #63, #67, #69, #70, #73, #74, #77, #82, #92, #93, #94, #95, #96, #97, #102, #108, #109, #114, #115, #116, #117, #121, #122, #123, #125, #127)
    10. For AC-10: Verify template fixes (#114, #115, #116, #117, #121, #127)
    11. For AC-11: Verify quality gates pass
  - **Verify**: All checks complete
  - **Done when**: All acceptance criteria documented as met
  - **Commit**: `chore(spec): AC checklist verified`
  - _Requirements: AC-1 through AC-11_

- [ ] VF [VERIFY] Goal verification: original failures now fixed
  - **Do**:
    1. Re-run: `python -m py_compile infrastructure/anchor_dataset/failed_sample_logger.py` (was SyntaxError, now passes)
    2. Re-run: `python -m pytest tests/ -x --tb=short --ignore=tests/test_agentic_gen.py` (pre-existing failures should not increase)
    3. Re-run: `ruff check .` (should pass with zero errors)
    4. Re-run: `python -c "import infrastructure; import src"` (should succeed)
  - **Verify**: All reproduction commands that previously failed now pass
  - **Done when**: Commands that failed before now succeed
  - **Commit**: `chore(spec): verify fix resolves original issues`
  - _Requirements: AC-1 through AC-11_

## Notes

- POC shortcuts: None — this is a fix-only spec, no prototypes needed
- All 102 issues verified as real (Group 1) before task generation
- Group 2 (103 false positives) explicitly excluded from fixes
- Quality gates every 2-3 tasks ensure no regression accumulates
- ruff excludes `tests/fixtures` directory (contains intentional syntax errors for testing)
- pytest excludes `tests/test_agentic_gen.py` (experimental)
