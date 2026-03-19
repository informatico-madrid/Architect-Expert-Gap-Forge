# Quickstart: Fix 37 Failing Tests

**Feature**: 011-fix-failing-tests  
**Branch**: `011-fix-failing-tests`

## Verification

Run the failing groups individually to confirm each fix:

```bash
# Full suite — target: 0 failed
cd /mnt/bunker_data/ai/data_factory
source .venv/bin/activate
PYTHONPATH=. pytest --tb=short -q

# Fix A — calibration schema (10 tests)
PYTHONPATH=. pytest tests/test_audit_calibration.py tests/test_inference.py \
  -k "calibration or Gemini" --tb=short

# Fix B — CLIError contract (5 tests)
PYTHONPATH=. pytest tests/test_model_evaluator_error_cases.py \
  tests/test_model_evaluator_integration_paths.py \
  -k "propagates_error or requires_dataset or validates_missing" --tb=short

# Fix C — llm_judge_score mock (2-3 tests)
PYTHONPATH=. pytest tests/test_model_evaluator.py::TestCmdScorePhase5 --tb=short

# Fix D — php_hexagonal.yaml config (4 tests)
PYTHONPATH=. pytest tests/unit/test_example_configs.py --tb=short

# Fix E — Gemini GOOGLE_API_KEY env mock (5 tests)
PYTHONPATH=. pytest tests/test_inference.py \
  -k "gemini or Gemini" --tb=short

# Fix F — doc loader monkeypatch (1 test)
PYTHONPATH=. pytest tests/test_model_evaluator_config_and_cli.py \
  ::TestLoadMasterDocsIntegration --tb=short
```

## Implementation Order

Fixes are independent and can be applied in any order. Recommended order by risk (lowest first):

1. **Fix D** — Create `php_hexagonal.yaml` and fix `multi_legacy.yaml` header. Pure file creation/edit, zero risk.
2. **Fix B** — Update test assertions `SystemExit` → `CLIError`. Test-only change.
3. **Fix E** — Add `GOOGLE_API_KEY` env mocks to inference tests. Test-only change.
4. **Fix F** — Add `monkeypatch` to `test_load_master_docs_file_reading`. Test-only change.
5. **Fix C** — Add `llm_judge_score` mock to `TestCmdScorePhase5`. Test-only change.
6. **Fix A** — Remove `top_p` from `calibration_schema.py` and `calibration.py`. Source change — run full suite after.

## Key File Locations

| File | Purpose |
|------|---------|
| `src/audit/calibration_schema.py` | `SamplingProfile`, `CALIBRATION_GRID`, `VALID_PARAMETERS` definitions |
| `src/audit/calibration.py` | `generate_profiles()` — two `SamplingProfile(...)` calls with `top_p` |
| `configs/stage_1_discovery/examples/php_hexagonal.yaml` | New example config to create |
| `configs/stage_1_discovery/examples/multi_legacy.yaml` | Needs AEGF copyright header added |
| `tests/test_model_evaluator_error_cases.py` | Fix `SystemExit` → `CLIError` (2 tests) |
| `tests/test_model_evaluator_integration_paths.py` | Fix `SystemExit` → `CLIError` (3 tests) |
| `tests/test_model_evaluator.py` | Add `llm_judge_score` mock (2 tests in `TestCmdScorePhase5`) |
| `tests/test_inference.py` | Add `GOOGLE_API_KEY` env mock (3 tests) |
| `tests/test_model_evaluator_config_and_cli.py` | Add `monkeypatch` + AEGF_DOC_ vars (1 test) |

## Expected Outcome

```
37 failed → 0 failed
1092 passed → 1129 passed
```
