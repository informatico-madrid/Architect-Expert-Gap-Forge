# Data Model: Fix 37 Failing Tests

**Feature**: 011-fix-failing-tests  
**Date**: 2026-03-19

This feature is a test-suite correctness fix. There are no new persistent entities. The only structural change is to an existing dataclass (`SamplingProfile`) and a YAML config constant (`CALIBRATION_GRID`).

---

## Affected Entity: `SamplingProfile`

**File**: `src/audit/calibration_schema.py`  
**Type**: `@dataclass(slots=True, frozen=True)`

### Current State (failing)

| Field | Type | Default | Validation |
|-------|------|---------|-----------|
| `temperature` | `float` | required | `[0.0, 2.0]` |
| `top_p` | `float` | required | `[0.0, 1.0]` ← REMOVE |
| `top_k` | `int` | required | `>= 0` |
| `min_p` | `float` | required | `[0.0, 1.0]` |
| `repetition_penalty` | `float` | required | `[0.5, 2.0]` |
| `presence_penalty` | `float` | required | `[-2.0, 2.0]` |

### Target State (green tests)

| Field | Type | Default | Validation |
|-------|------|---------|-----------|
| `temperature` | `float` | required | `[0.0, 2.0]` |
| `top_k` | `int` | required | `>= 0` |
| `min_p` | `float` | required | `[0.0, 1.0]` |
| `repetition_penalty` | `float` | required | `[0.5, 2.0]` |
| `presence_penalty` | `float` | required | `[-2.0, 2.0]` |

---

## Affected Constant: `CALIBRATION_GRID`

**File**: `src/audit/calibration_schema.py`

### Current State (failing)

```python
CALIBRATION_GRID: Final[dict[str, list[Any]]] = {
    "temperature": [...],
    "top_p": [0.7, 0.8, 0.9, 0.95, 1.0],   # ← REMOVE
    "top_k": [...],
    "min_p": [...],
    "repetition_penalty": [...],
}
```

### Target State

```python
CALIBRATION_GRID: Final[dict[str, list[Any]]] = {
    "temperature": [...],
    "top_k": [...],
    "min_p": [...],
    "repetition_penalty": [...],
}
```

---

## Affected Constant: `VALID_PARAMETERS`

**File**: `src/audit/calibration_schema.py`

### Current State (failing)

```python
VALID_PARAMETERS: Final[set[str]] = {
    "temperature",
    "top_p",        # ← REMOVE
    "top_k",
    "min_p",
    "repetition_penalty",
    "presence_penalty",
}
```

### Target State

```python
VALID_PARAMETERS: Final[set[str]] = {
    "temperature",
    "top_k",
    "min_p",
    "repetition_penalty",
    "presence_penalty",
}
```

---

## New Config File: `php_hexagonal.yaml`

**Path**: `configs/stage_1_discovery/examples/php_hexagonal.yaml`

### Required Keys (from `test_example_configs.py`)

| Key | Type | Value |
|-----|------|-------|
| `profile` | `str` | `"php_hexagonal"` (must match `master_docs_map.yaml` entry) |
| `display_name` | `str` | Human-readable name |
| `description` | `str` | Free text |
| `extractor` | `dict` | Must contain `on_parse_error` ∈ `{abort, skip, fallback}` |
| `module_discovery` | `dict` | Must contain `strategy` |

---

## Test Behavior Changes (no schema changes)

| Test File | Change | Type |
|-----------|--------|------|
| `test_model_evaluator_error_cases.py` | `SystemExit` → `CLIError` in 2 tests | Test assertion fix |
| `test_model_evaluator_integration_paths.py` | `SystemExit` → `CLIError` in 3 tests | Test assertion fix |
| `test_model_evaluator.py` | Add `patch("src.audit.cli.llm_judge_score")` in 2 tests | Mock addition |
| `test_inference.py` | Add `patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-ci-key"})` in 3-5 tests | Env isolation |
| `test_model_evaluator_config_and_cli.py` | Add `monkeypatch` + `AEGF_DOC_*` setenv in 1 test | Env isolation |
