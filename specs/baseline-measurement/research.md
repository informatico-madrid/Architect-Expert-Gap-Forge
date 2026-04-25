# Research: Baseline Measurement

**Spec**: baseline-measurement
**Epic**: aegf-infrastructure (Epic 0)
**Date**: 2026-04-25
**Python**: 3.14.3
**Phase**: Research

---

## Executive Summary

The baseline-measurement spec requires capturing pre-DSPy metrics across three dimensions: **calibration quality** (grid search over sampling parameters with LDI and coherence scores), **Spearman correlation** (rank-order agreement between baseline and adapter judge scores), and **benchmark methodology** (standardized I/O for repeatable measurement). Critical findings: (1) **scipy is NOT in requirements.txt** despite being required for Spearman — this is a dependency gap the dependency-compatibility spec missed; (2) **LDI is NOT a calibration metric** — it's a curation/pipeline quality filter; (3) all scipy versions (1.16.3, 1.17.0, 1.17.1) have identical wheel coverage across Python 3.11-3.14 — no Python version forcing is needed.

---

## 1. Spearman Correlation Baseline

### Scoring Pipeline

`judge.py` (`src/audit/judge.py`) uses `NormalizedJudgeResponse` defined in `src/audit/schema.py:81`:

```python
class NormalizedJudgeResponse(TypedDict):
    baseline: dict[str, float]
    adapter: dict[str, float]
    reasoning: str
```

A second, more lenient definition exists in `src/schemas/common.py:67` with `total=False`.

### Judge Dimension Scores and Weights

**SCORING_WEIGHTS** (Stage 5, `src/audit/schema.py:39-45`):

| Dimension | Weight |
|-----------|--------|
| ha_modernity | 0.30 |
| reasoning_depth | 0.25 |
| functionality | 0.25 |
| completeness | 0.12 |
| style | 0.08 |

**CALIBRATION_SCORING_WEIGHTS** (Stage 6, `src/audit/schema.py:49-55`):

| Dimension | Weight |
|-----------|--------|
| parameter_effectiveness | 0.30 |
| task_completion | 0.20 |
| parameter_alignment | 0.25 |
| coherence | 0.15 |
| style | 0.10 |

### Composite Score Calculation

Two paths exist in the codebase:

**Path A — scorecard.py** (`src/audit/scorecard.py:68-70`), **Stage 5 evaluation**:
```python
def _composite(scores: dict[str, float]) -> float:
    return sum(scores.get(dim, 0.0) * weight for dim, weight in SCORING_WEIGHTS.items())
```
Always uses SCORING_WEIGHTS regardless of context (no auto-detect).

**Path B — calibration.py** (`src/audit/calibration.py:1557-1592`), **Stage 6**:
```python
def calculate_composite_score(judge_scores, weights=None):
    if weights is None:
        if "parameter_effectiveness" in judge_scores:
            weights = CALIBRATION_SCORING_WEIGHTS  # Stage 6
        else:
            weights = SCORING_WEIGHTS              # Stage 5
```
Auto-detects based on dimension keys present.

**Gap**: `_composite()` in scorecard.py does NOT use this logic; it always uses SCORING_WEIGHTS.

**Decision**: Use `SCORING_WEIGHTS` (ha_modernity keys) for Spearman baseline. The fixture data uses Stage 5 dimensions.

### Reference Datasets

| Fixture | Path | Format | Samples |
|---------|------|--------|---------|
| calibration_examples.json | `tests/fixtures/calibration_examples.json` | JSON | **4** calibration_results entries |
| judge_scoring_response.json | `tests/fixtures/judge_scoring_response.json` | JSON | Full judge output |
| inference_results.json | `tests/fixtures/inference_results.json` | JSON | baseline + adapter responses |
| seed_examples.yaml | `tests/fixtures/seed_examples.yaml` | YAML | 100+ seed examples |

**Note**: calibration_examples.json has 4 calibration_results (not 5 — research originally confused with sample_prompts count of 5). All entries use Stage 5 dimensions (ha_modernity keys), NOT calibration dimensions.

### scipy.stats.spearmanr Pattern

```python
from scipy.stats import spearmanr

def compute_spearman_baseline(
    baseline_composites: list[float],
    adapter_composites: list[float],
) -> dict:
    n = len(baseline_composites)
    if n < 3:
        return {"rho": float("nan"), "p_value": float("nan"), "n": n,
                "pass_target": False, "reason": "insufficient_samples"}
    if len(set(baseline_composites)) <= 1 or len(set(adapter_composites)) <= 1:
        return {"rho": 0.0, "p_value": 1.0, "n": n,
                "pass_target": False, "reason": "constant_input"}
    method = "exact" if n < 10 else "asymptotic"
    rho, p_value = spearmanr(baseline_composites, adapter_composites, method=method)
    return {"rho": float(rho), "p_value": float(p_value), "n": n,
            "method": method, "pass_target": bool(rho > 0.8)}
```

### NFR-002 Target

Spearman correlation > 0.8 is the validation target.

**Sources**:
- `specs/_epics/aegf-infrastructure/epic.md:166`: "Spearman correlation > 0.8 with existing judge.py scores (no regression)"
- `specs/baseline-measurement/plan.md:11`: "NFR-002 (Spearman >0.8)"

This is a **spec-level requirement** only — no Python constant or assertion implements this target in code.

### Edge Cases

1. **n < 3**: Spearman undefined — return structured error
2. **n = 3-5**: Use `method='exact'` (p-values unreliable for small n)
3. **Ties**: scipy handles via average ranks (unlikely with float scores)
4. **Constant input**: scipy raises `ConstantInputError` — detect and return structured error

---

## 2. Calibration Quality Baseline (LDI, Coherence)

### LDI (Length Density Index) — NOT a Calibration Metric

**LDI is a curation/pipeline quality filter, not a calibration scoring dimension.** Two separate implementations exist with DIFFERENT formulas and K values.

**Factory LDI** (`src/factory/ldi_validator.py:76-108`):
```python
ldi = round(code_len / reasoning_len, 3)
K = 1200
dynamic_limit = 0.10 * (code_len / (code_len + K))
# Passes if ldi >= dynamic_limit
```
- Character-level analysis
- K = 1200 for dynamic threshold
- Used in Stage 1 (factory) data generation validation
- Micro-snippet exception: code_len < 100 chars with LDI > 0.01 always passes

**Curation LDI** (`src/curation/quality_filter.py:146-156`):
```python
K = 800.0  # Factor de estabilidad para registros cortos (calibrado)
ldi_score = code_tokens / max(1.0, (natural_tokens + code_tokens))
ldi_final = ldi_score * (code_tokens / (code_tokens + K))
```
- Token-level analysis
- K = 800 for short-record stability
- Uses different denominator: `(natural_tokens + code_tokens)` instead of `reasoning_len`
- Used in Stage 3 (curation) structural quality filtering

**Source for baseline**: LDI must come from curation pipeline outputs or `SampleRecord.ldi` (`src/audit/schema.py:129`) — NOT from calibration results.

### Coherence — IS a Calibration Metric

Coherence is a judge-dimension score (0.0-1.0) scored by the LLM judge, weighted at **15%** in calibration scoring:

| Dimension | Weight | Source |
|-----------|--------|--------|
| parameter_effectiveness | 0.30 | Judge score |
| task_completion | 0.20 | Judge score |
| parameter_alignment | 0.25 | Judge score |
| **coherence** | **0.15** | **Judge score** |
| style | 0.10 | Judge score |

**Source**: `src/audit/schema.py:49-55` (`CALIBRATION_SCORING_WEIGHTS`)

Coherence is directly available in `CalibrationResult.judge_scores["coherence"]` — straightforward to extract.

**Grid search does NOT use LDI**: `src/audit/calibration.py` contains zero LDI-related code (verified via grep). LDI only lives in factory and curation stages.

### Grid Search Configuration

**Source**: `src/audit/calibration_schema.py:66-72`

| Parameter | Values | Count |
|-----------|--------|-------|
| temperature | [0.3, 0.5, 0.6, 0.7, 0.9, 1.1] | 6 |
| top_k | [5, 10, 20, 40, 60, 80] | 6 |
| min_p | [0.0, 0.02, 0.05, 0.1, 0.15] | 5 |
| repetition_penalty | [1.0, 1.05, 1.1, 1.15, 1.2] | 5 |
| presence_penalty | [0.0, 0.5, 1.0, 1.5, 2.0] | 5 |

**Profile count**: 6 × 6 × 5 × 5 × 5 = **4,500 profiles**
**Total with 6 prompts**: 4,500 × 6 = **27,000 API calls**

### CalibrationReport Schema

**Source**: `src/audit/calibration_schema.py:209-251`

```python
@dataclass(slots=True, frozen=True)
class CalibrationReport:
    timestamp: str
    total_iterations: int
    best_profile: SamplingProfile
    best_score: float
    all_results: list[CalibrationResult]
    statistics: dict[str, Any] = field(default_factory=dict)
    prompt_count: int = 0
    focus_analysis: dict[str, Any] = field(default_factory=dict)
```

Statistics object includes: mean_composite_score, std_composite_score, min_composite_score, max_composite_score, profiles_tested, prompts_tested, short_responses_penalized, mean_response_length, execution_time_seconds.

---

## 3. Dependency Analysis

### scipy Dependency Gap

| Package | requirements.txt | pyproject.toml | Status |
|---------|-----------------|----------------|--------|
| numpy | ==2.4.4 | ==2.4.4 | Pinned (was pre-existing bug, now fixed) |
| **scipy** | **MISSING** | **MISSING** | **CRITICAL GAP — required for Spearman** |

scipy is NOT in requirements.txt, pyproject.toml, infrastructure/dependency_check.py PACKAGE_IMPORT_MAP, or any source imports. Verified via:
- `pip index versions scipy` — confirms scipy versions available
- `grep -rn 'import scipy\|from scipy' src/ scripts/` — zero matches

### scipy Wheel Availability (Verified via PyPI + pip download)

All three scipy versions have **identical wheel coverage** (60 wheels each, 0 yanked):

| Attribute | 1.16.3 | 1.17.0 | 1.17.1 (latest) |
|-----------|--------|--------|-----------------|
| cp311 wheels | 10 | 10 | 10 |
| cp312 wheels | 10 | 10 | 10 |
| cp313 wheels | 20 | 20 | 20 |
| cp314 wheels | 20 | 20 | 20 |
| Total files | 61 | 61 | 61 |
| Yanked | No | No | No |
| Numpy requirement | `numpy<2.6,>=1.25.2` | `numpy<2.7,>=1.26.4` | `numpy<2.7,>=1.26.4` |
| manylinux tag | manylinux2014 | manylinux_2_27 | manylinux_2_27 |

**All pip download tests succeeded**:
- scipy 1.17.0 on Python 3.12, 3.13, 3.14 — all succeed
- scipy 1.17.1 on Python 3.12, 3.13, 3.14 — all succeed
- scipy 1.16.3 on Python 3.12, 3.13, 3.14 — all succeed

### numpy Wheel Availability

| Attribute | 2.2.6 | 2.4.4 (current) |
|-----------|-------|-----------------|
| cp310 wheels | 10 | 0 |
| cp311 wheels | 10 | 11 |
| cp312 wheels | 10 | 11 |
| cp313 wheels | 20 | 21 |
| cp314 wheels | **0** | 21 |
| Total files | 55 | 72 |
| Yanked | No | No |

**numpy 2.2.6 is NOT yanked** but has no cp314 wheels. On Python 3.14 it falls back to source tar.gz which may not build without a Fortran/C toolchain.

### Recommendation: scipy==1.17.1

Since scipy is not currently used in the codebase, any version is a prospective choice:

- **scipy==1.17.1** (latest) — same wheel coverage as 1.16.3, slightly newer numpy compatibility bounds (`<2.7`), no functional difference in wheel availability
- **scipy==1.16.3** (conservative) — most mature, older API, proven stable
- **scipy==1.17.0** — between the two, same wheels as 1.17.1

**No version is problematic for wheel availability on any Python 3.11-3.14.** The original research's core claims about missing wheels for specific Python versions were entirely incorrect.

If scipy must be added to the project:
```toml
[project.optional-dependencies]
scipy = [
    "scipy>=1.17.1,<1.18",
    "numpy>=2.4.0,<2.5",
]
```

Or as a hard dependency:
```
requirements.txt: scipy==1.17.1
pyproject.toml: scipy==1.17.1
```

### Files to Modify for scipy

| File | Change | Priority |
|------|--------|----------|
| `requirements.txt` | Add `scipy==1.17.1` | REQUIRED |
| `pyproject.toml` | Add `scipy==1.17.1` to dependencies (or optional) | REQUIRED |
| `infrastructure/dependency_check.py` | Add `scipy: ("scipy",)` to PACKAGE_IMPORT_MAP | REQUIRED |

---

## 4. Benchmark Patterns & Directory Structure

### Existing Benchmark Scripts

Two distinct coding patterns exist in the benchmark directory:

| Script | Path | Lines | Pattern Type |
|--------|------|-------|-------------|
| compare_baseline.py | `scripts/benchmark/compare_baseline.py` | 224 | **Simple** (print-based CLI) |
| dependency_check.py | `infrastructure/dependency_check.py` | 274 | **Rich** (typed, testable) |
| measure_performance.py | `scripts/benchmark/measure_performance.py` | varies | numpy + sys.path |

### Pattern 1: compare_baseline.py (Simple — for benchmark scripts)

```python
def main():
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--current", required=True)
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--profile", default="homeassistant")
    args = parser.parse_args()
    # ... work ...
    if error:
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

- **NO** argv parameter
- **NO** return type annotation
- **NO** `_die()` function
- **NO** `logging.basicConfig` — uses `print()` + `sys.stderr`
- **sys.exit(1)** in 3 places for fatal errors
- **NO** `raise SystemExit(main())` wrapper
- 6 argparse args: `--current`, `--baseline`, `--profile`, `--threshold`, `--output`, `--verbose`
- JSON output: `json.dump(output_data, f, indent=2)` (line 214)

### Pattern 2: dependency_check.py (Rich — for infrastructure tools)

```python
def _die(msg: str) -> NoReturn:
    """Print an error message to stderr and exit with code 1."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )
    parser = argparse.ArgumentParser(description="...")
    # ... args ...
    return 0  # or 1

if __name__ == "__main__":
    raise SystemExit(main())
```

- **Has** typed argv parameter: `argv: list[str] | None = None`
- **Has** return type: `-> int`
- **Has** `_die(msg: str) -> NoReturn` helper
- **Has** `logging.basicConfig` + `logging.getLogger(__name__)`
- **Has** `raise SystemExit(main())` wrapper
- 1 argparse arg: `--check`

### Recommendation for New Scripts

| Location | Pattern | Rationale |
|----------|---------|-----------|
| `scripts/benchmark/` | compare_baseline.py (simple) | Consistent with existing benchmark scripts |
| `infrastructure/` tools | dependency_check.py (rich) | Testable with argv injection, structured logging |
| **DO NOT mix patterns** in one file | | |

### Directory Structure

```
infrastructure/
    __init__.py              # EXISTS but EMPTY
    baselines/               # DOES NOT EXIST — must be created
scripts/benchmark/
    baselines/
        homeassistant.json   # EXISTS — 676 bytes, performance benchmark data
    compare_baseline.py      # 224 lines
    measure_performance.py
```

**Baseline data storage**: `scripts/benchmark/baselines/` (existing)
**Proposed output directory**: `baseline_results/` at project root (does NOT exist yet)
**Proposed baseline scripts**: `infrastructure/baselines/` (does NOT exist yet — plan.md line 63 confirms "infrastructure/ directory does NOT exist -- must be created")

---

## 5. Coding Conventions

### Constitution-Enforced Headers

**check_headers.py** (`scripts/check_headers.py`) validates 3 tokens within first 4096 bytes:

```python
HEADER_TOKENS = ("SPDX-License-Identifier:", "Architect-Expert-Gap-Forge", "Copyright")
```

Scans: `src/`, `tests/`, `docs/`, `scripts/`, `deploy/`, `diagnose/`, `examples/`, `legacy/`, `infrastructure/`.

Actual header format in `scripts/benchmark/` (7 lines, compare_baseline.py):
```python
#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
```

Note: actual headers vary — `dependency_check.py` uses 6 lines without Source URL and with `# -*- coding: utf-8 -*-` line. Only the 3 tokens are enforced.

### Import Organization

```python
from __future__ import annotations   # ALWAYS first
import stdlib                         # alphabetical
from third_party                      # alphabetical
from src.module import ...           # local imports
```

### Docstring Style

**Standalone scripts**: Block docstring with Usage section:
```python
"""
Module description.

Usage:
    python path/to/script.py --arg value
"""
```

**Google-style function docstrings**: Args, Returns, Raises sections.

### Logging

Two patterns coexist in the codebase:

**`src/utils/logging.py`** uses `RichHandler` for formatted terminal output:
```python
format: "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s"
```

**Neither benchmark script uses the shared get_logger()** — they do their own thing:
- compare_baseline.py: print() + sys.stderr
- dependency_check.py: logging.basicConfig + logger = getLogger(__name__)

### Custom Exceptions

**src/utils/exceptions.py** defines 5 exception classes:
- `ConfigValidationError(ValueError)` — config validation failures
- `NormalizationError(ValueError)` — data format normalization failures
- `CheckpointError(IOError)` — checkpoint read/write failures
- `DeduplicationError(ValueError)` — deduplication logic errors
- `TeacherAPIError(RuntimeError)` — Teacher model API call failures

### Tools & Linting

- **Formatter**: `ruff format` (dev dependency)
- **Type checker**: `pyright`
- **Test framework**: `pytest` with markers `unit`, `integration`, `slow`

---

## 6. Related Specs

| Spec | Relationship | Status |
|------|-------------|--------|
| `dependency-compatibility` | Added numpy==2.4.4 but MISSED scipy | Completed |
| `prompt-externalization` | Creates .example.yaml templates for DSPy | Completed |
| `anchor-dataset` | Pending spec in same epic | Pending |
| `aegf-dspy-integration` (Epic 1) | Post-baseline implementation target | Planning |

### Source Bug Corrections from Prompt Externalization

These 7 issues were discovered during prompt-externalization and must be addressed in Epic 1 DSPy integration:

| # | Issue | Severity | Target Story |
|---|-------|----------|--------------|
| 1 | Typo "Architecture architecture" | LOW | 1.4 (JudgeSignature) |
| 2 | Calibration parameter_target structure | MEDIUM | 1.6 (CalibrationSignature) |
| 3 | $var vs {var} inconsistency | MEDIUM | 1.1 (TrajectorySignature) |
| 4 | </think> trailing space | LOW | 1.4 (JudgeSignature) |
| 5 | Python vs Jinja output protocol | FALSE POSITIVE | None |
| 6 | Forbidden terms undocumented | MEDIUM | 1.7 (Hard Query) |
| 7 | Dead code frontend_taxonomy_prompts.py | LOW | 1 or cleanup |

---

## 7. Open Questions

1. **LDI data source**: Where does the calibration baseline script get LDI data from — existing curation outputs, SampleRecord files, or must it run the curation pipeline?
2. **Grid size for baseline**: Should the calibration baseline run the full 4,500-profile grid, or a subset for speed? (27,000 API calls total)
3. **LLM dependency for Spearman**: Should the baseline script require a live LLM API call, or read pre-computed scores from fixtures? (Only 4 calibration_examples.json entries available)
4. **scipy as hard vs optional dependency**: Since scipy works on all Python 3.11-3.14 with identical wheel coverage, is it worth making optional, or should it be a hard dependency?

---

## Sources

| Source | Key Point |
|--------|-----------|
| `src/audit/schema.py:39-45` | SCORING_WEIGHTS — 5 dimensions, exact weights verified |
| `src/audit/schema.py:49-55` | CALIBRATION_SCORING_WEIGHTS — 5 calibration dimensions |
| `src/audit/schema.py:81` | NormalizedJudgeResponse TypedDict |
| `src/audit/scorecard.py:68-70` | _composite() — always uses SCORING_WEIGHTS |
| `src/audit/calibration.py:1557-1592` | calculate_composite_score() — auto-detects weights |
| `src/audit/calibration_schema.py:66-72` | CALIBRATION_GRID — 5 params, 4,500 profiles |
| `src/audit/calibration_schema.py:209-251` | CalibrationReport schema |
| `src/factory/ldi_validator.py:76-108` | Factory LDI — K=1200, character-level |
| `src/curation/quality_filter.py:146-156` | Curation LDI — K=800, token-level |
| `src/audit/schema.py:129` | SampleRecord.ldi field |
| `scripts/benchmark/compare_baseline.py` | 224 lines — simple CLI pattern |
| `infrastructure/dependency_check.py` | 274 lines — rich CLI pattern |
| `tests/fixtures/calibration_examples.json` | 4 calibration_results entries, Stage 5 dims |
| `pyproject.toml` | requires-python = ">=3.12", numpy==2.4.4 |
| `requirements.txt` | numpy==2.4.4 pinned, scipy MISSING |
| `scripts/check_headers.py:40-44` | 3 header tokens enforced |
| `src/utils/logging.py` | get_logger() with RichHandler |
| `src/utils/exceptions.py` | 5 custom exception classes |
| `specs/baseline-measurement/plan.md` | ACs, interface contracts, dependency notes |
| `specs/_epics/aegf-infrastructure/epic.md` | Story 0.1, NFR-002 Spearman >0.8 |
| `_bmad-output/planning-artifacts/epics.md` | BMAD original stories |
