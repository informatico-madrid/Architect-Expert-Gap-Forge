# Research: Fix 37 Failing Tests

**Feature**: 011-fix-failing-tests  
**Date**: 2026-03-19  
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## Decision 1: Remove or keep `top_p` in `SamplingProfile`

**Decision**: Remove `top_p` from `SamplingProfile`, `CALIBRATION_GRID`, and `VALID_PARAMETERS`.

**Rationale**: Live introspection confirms `top_p` is currently present in `calibration_schema.py`. The entire test suite for `test_audit_calibration.py` was written expecting `top_p` NOT to exist — all 10 failing tests instantiate `SamplingProfile` without `top_p` and define grids without it. The test for `VALID_PARAMETERS` explicitly asserts the set `{temperature, top_k, min_p, repetition_penalty, presence_penalty}` — excluding `top_p`. Conclusion: a recent change added `top_p` back to `calibration_schema.py` without updating the tests. The spec (tests) is the source of truth here; the source code must align.

**Files to change**:
- `src/audit/calibration_schema.py`: Remove `top_p` from `SamplingProfile` fields, validation, `from_dict()`, `CALIBRATION_GRID`, and `VALID_PARAMETERS`.
- `src/audit/calibration.py` lines 754–755 and 1426–1427: Remove `top_p=...` from the two `SamplingProfile(...)` constructor calls inside `generate_profiles()`.

**Alternatives considered**:
- Update all tests to include `top_p` — rejected because it would require changing ~10 test methods and `top_p` was deliberately removed from the spec design (tests are the spec).
- Mark tests as `xfail` — rejected as an anti-pattern that hides regression.

---

## Decision 2: `CLIError` vs `SystemExit` in CLI error tests

**Decision**: Update the 5 failing tests to use `pytest.raises(CLIError)` instead of `pytest.raises(SystemExit)`.

**Rationale**: Constitution §III explicitly states "Do not use `SystemExit` for flow-control." The CLI `cmd_sample`, `cmd_generate_exam` already raise `CLIError` for all error paths — this is intentional and correct. The tests in `test_model_evaluator_error_cases.py` and `test_model_evaluator_integration_paths.py` were written expecting `SystemExit` (an older contract) but never updated when the CLI was refactored to use typed exceptions.

**Specific tests to update** (5 total):
- `test_model_evaluator_error_cases.py::TestCmdGenerateGapErrorCases::test_cmd_sample_propagates_error_from_generate_gap_analysis`
- `test_model_evaluator_error_cases.py::TestCmdGenerateExamErrorCases::test_generate_exam_raises_propagates_error_from_generate_exam_question`
- `test_model_evaluator_integration_paths.py::TestCmdSampleProcessing::test_cmd_sample_requires_dataset_for_generation`
- `test_model_evaluator_integration_paths.py::TestCmdGenerateExamLoop::test_cmd_generate_exam_validates_missing_metadata`
- `test_model_evaluator_integration_paths.py::TestCmdGenerateExamErrorPropagation::test_cmd_generate_exam_propagates_prompt_generation_error`

**Import**: All test files already import `CLIError` from `src.audit.cli` (or `src.audit.schema`).  
Check: `from src.audit.cli import CLIError` is present in both test files.

**Alternatives considered**:
- Revert the CLI to use `sys.exit()` — rejected because it violates the constitution and loses typed exception information.

---

## Decision 3: Missing `llm_judge_score` mock in `TestCmdScorePhase5`

**Decision**: Add `patch("src.audit.cli.llm_judge_score", return_value=mock_judge)` to both `TestCmdScorePhase5` test methods.

**Rationale**: `cmd_score` (line 311 of `src/audit/cli.py`) calls `llm_judge_score(...)` before calling `compute_scorecard(...)`. The tests only mocked `compute_scorecard`, leaving `llm_judge_score` to make a real HTTP call to `http://localhost:8000/v1/chat/completions` — which doesn't exist in CI. A minimal `NormalizedJudgeResponse` dict (with `baseline`, `adapter`, `reasoning` keys) satisfies `compute_scorecard`'s input requirement.

**Mock value**:
```python
mock_judge_resp: NormalizedJudgeResponse = {
    "baseline": {"ha_modernity": 0.8},
    "adapter": {"ha_modernity": 0.9},
    "reasoning": "mock",
}
```

**Alternatives considered**:
- Refactor `cmd_score` to accept an injected judge function — rejected as over-engineering for a test fix.
- Use `responses` library to intercept HTTP — rejected as adds a dependency for a unit test concern.

---

## Decision 4: Create `php_hexagonal.yaml` and fix `multi_legacy.yaml` header

**Decision**: Create `configs/stage_1_discovery/examples/php_hexagonal.yaml` with the full AEGF copyright header and all required keys. Fix `multi_legacy.yaml` to add the AEGF copyright block before its existing content.

**Rationale**: The test `test_php_hexagonal_example_exists` asserts the file exists. The test `test_example_configs_have_file_header` checks all `*.yaml` files in `examples/` for `"Architect-Expert-Gap-Forge (AEGF)"`, `"Copyright"`, and `"Apache License"`. `multi_legacy.yaml` currently starts with `# AEGF Stage 1 Discovery Config — osCommerce Legacy PHP` without the standard copyright block.

**Required keys** (from test + master_docs_map.yaml):
- `profile: php_hexagonal` (matches entry in `master_docs_map.yaml`)
- `display_name`, `description`, `extractor` (with `on_parse_error`), `module_discovery`

**Header template** (from `homeassistant.yaml`):
```yaml
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
```

**Alternatives considered**:
- Update the test to accept an alternative header format — rejected because the test validates the AEGF governance policy itself.

---

## Decision 5: Gemini tests need `GOOGLE_API_KEY` env mock

**Decision**: Add `with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-ci-key"}):` around `router.professor(backend="gemini", ...)` calls in `TestInferenceRouterGeminiPaths` and around `InferenceRouter._resolve_backend("gemini")` in `test_explicit_gemini_passes_through`.

**Rationale**: `InferenceRouter._resolve_backend()` checks `os.getenv("GOOGLE_API_KEY")` before creating a Gemini client. The tests correctly patch `GeminiClient` but omit the env var guard. `TestGeminiClientWithMock` already uses `patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-ci-key"})` inside `_make_client()` — this is the established pattern.

**Tests to fix** (5 total):
- `TestInferenceRouterGeminiPaths::test_professor_creates_gemini_client_when_backend_is_gemini`
- `TestInferenceRouterGeminiPaths::test_professor_gemini_client_is_cached`
- `TestInferenceRouterGeminiPaths::test_student_creates_gemini_client_when_backend_is_gemini` (currently passing — no change needed)
- `TestInferenceRouterResolveBackend::test_explicit_gemini_passes_through`
- `TestGeminiClientWithMock` methods that call `generate()` outside of `_make_client()` context

**Alternatives considered**:
- Move the `GOOGLE_API_KEY` check to client instantiation instead of backend resolution — rejected as a logic change beyond the scope of this fix.

---

## Decision 6: `test_load_master_docs_file_reading` needs env var isolation

**Decision**: Add `monkeypatch` parameter to `test_load_master_docs_file_reading` and set `AEGF_DOC_1=reference_guide.md`, `AEGF_DOC_2=technical_changelog.md`, `AEGF_DOC_3=syntax_guide.md` to bypass the config file resolution.

**Rationale**: `load_master_docs()` has a 3-level cascade: env vars → YAML config → internal defaults. The YAML config at `configs/stage_5_evaluation/eval_config.yaml` maps to `HA_MASTER_GUIDE_2026.md` etc., overriding defaults. The test creates `reference_guide.md`, `technical_changelog.md`, `syntax_guide.md` in `tmp_path` (matching the internal defaults), but the YAML config intercepts and substitutes HA-specific filenames. Setting env vars bypasses the config cascade.

**Alternatives considered**:
- Create files with HA names (`HA_MASTER_GUIDE_2026.md`, etc.) in `tmp_path` — would make the test less readable (the test intent is to verify the loader reads any 3 files, not HA-specific ones).
- Patch `_DEFAULT_CONFIG_PATH.exists()` to return `False` — fragile private-API patching.
- Use `monkeypatch.chdir(tmp_path)` to change the working directory — does not work because `_DEFAULT_CONFIG_PATH` is an absolute path off the repo root.
