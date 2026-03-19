# Implementation Plan: Fix 37 Failing Tests

**Branch**: `011-fix-failing-tests` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-fix-failing-tests/spec.md`

## Summary

37 tests fail due to 6 independent spec/implementation mismatches introduced by recent changes. The fixes are surgical and span two categories: (1) source corrections (removing `top_p` from the calibration schema, fixing config file headers/creation) and (2) test corrections (updating error contract assertions, adding missing mocks). No new logic is introduced.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: pytest 9.0, dataclasses, unittest.mock, PyYAML  
**Storage**: YAML config files, JSON test fixtures  
**Testing**: pytest with monkeypatch, `patch()`, `patch.dict()`  
**Target Platform**: Linux (CI / local developer machine)  
**Project Type**: Data-pipeline CLI  
**Performance Goals**: N/A — test correctness only  
**Constraints**: No new tests; no logic changes beyond schema alignment; CI must pass in <30s  
**Scale/Scope**: 6 isolated fix groups across ~10 files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Strict typing on all public functions | ✅ PASS | Existing functions keep their annotations; no signature changes in public API except removal of `top_p` from `SamplingProfile` which must be reflected in all callers. |
| Immutable dataclasses | ✅ PASS | `SamplingProfile` remains `@dataclass(frozen=True)` after removing the field. |
| No import-time side-effects | ✅ PASS | No new module-level I/O introduced. |
| No `SystemExit` for flow-control | ✅ PASS | Constitution §III explicitly forbids `SystemExit` for flow-control. CLI raises `CLIError` — correct. Tests must be updated to reflect this. |
| CI uses local mocks for external services | ⚠️ FIX NEEDED | Tests in `TestCmdScorePhase5`, `TestInferenceRouterGeminiPaths`, `TestGeminiClientWithMock` make real HTTP calls or require real `GOOGLE_API_KEY`. Must add mocks. |
| No silent failures | ✅ PASS | All fixes add or preserve explicit exceptions. |
| Header policy for new source files | ⚠️ FIX NEEDED | New `php_hexagonal.yaml` must include AEGF header. Existing `multi_legacy.yaml` is missing the header. |

**Post-constitution decision**: No violations requiring justification. All fixes align the codebase with existing constitution rules.

## Project Structure

### Documentation (this feature)

```text
specs/011-fix-failing-tests/
├── plan.md               ← This file
├── research.md           ← Phase 0 output
├── data-model.md         ← Phase 1 output
├── quickstart.md         ← Phase 1 output
└── tasks.md              ← Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code Changes (repository root)

```text
src/audit/calibration_schema.py          ← Remove top_p from SamplingProfile,
                                            CALIBRATION_GRID, VALID_PARAMETERS
src/audit/calibration.py                 ← Fix generate_profiles() top_p reference

configs/stage_1_discovery/examples/
├── php_hexagonal.yaml                   ← CREATE (new example config)
└── multi_legacy.yaml                    ← FIX header (add AEGF copyright block)

tests/test_model_evaluator_error_cases.py      ← Fix: SystemExit → CLIError
tests/test_model_evaluator_integration_paths.py ← Fix: SystemExit → CLIError
tests/test_model_evaluator.py                  ← Fix: add llm_judge_score mock
tests/test_inference.py                        ← Fix: add GOOGLE_API_KEY env mock
tests/test_model_evaluator_config_and_cli.py   ← Fix: add monkeypatch + AEGF_DOC_* vars
```

## Complexity Tracking

No violations requiring justification.

---

## Phase 0: Research & Unknowns

All NEEDS CLARIFICATION items resolved. Full details in [research.md](research.md).

| Unknown | Resolution |
|---------|-----------|
| Should `top_p` stay or go? | Remove. Tests are the spec — they assert `top_p` is absent from `SamplingProfile` and `VALID_PARAMETERS`. |
| `CLIError` or `SystemExit`? | `CLIError` — constitution §III forbids `SystemExit` for flow-control. Tests must match. |
| What does `llm_judge_score` return? | `NormalizedJudgeResponse` TypedDict — `baseline: dict[str, float]`, `adapter: dict[str, float]`, `reasoning: str`. |
| What header does `php_hexagonal.yaml` need? | Full AEGF copyright block — same as `homeassistant.yaml` (6 comment lines). |
| What keys does `php_hexagonal.yaml` need? | `profile`, `display_name`, `description`, `extractor.on_parse_error`, `module_discovery`. |
| Why does `test_load_master_docs_file_reading` fail? | `eval_config.yaml` overrides filename defaults to HA-specific names before the test's files can be found. Fix: env var isolation. |

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for full before/after comparison.

**Key change**: `SamplingProfile` loses `top_p` field. No other entity changes.

### Contracts

This project has no external API surface (library, REST, CLI public API). The "contract" is the pytest test suite itself — 37 tests define the expected behaviour. All fixes make the implementation match the tests, not the reverse.

No `/contracts/` directory is needed for this feature.

### Quickstart

See [quickstart.md](quickstart.md) for per-group verification commands and implementation order.

---

## Phase 0: Research — Post-Design Constitution Re-Check

| Gate | Post-Design Status |
|------|--------------------|
| Strict typing | ✅ PASS — `SamplingProfile` field removal requires no additional annotations |
| Immutable dataclasses | ✅ PASS — `frozen=True` unchanged |
| No `SystemExit` | ✅ PASS — test updates align with existing source behaviour |
| CI mocks | ✅ PASS — all missing mocks now documented in data-model.md |
| Header policy | ✅ PASS — `php_hexagonal.yaml` spec includes AEGF header |
