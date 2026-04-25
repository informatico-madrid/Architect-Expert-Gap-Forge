# Requirements: Baseline Measurement

**Spec**: baseline-measurement
**Epic**: aegf-infrastructure (Epic 0)
**Goal**: Capture pre-DSPy metrics across calibration quality, judge agreement, and compile duration so DSPy improvements are objectively measurable.

---

## User Stories

### US-1: Install scipy dependency
**Priority**: MUST
**Dependencies**: Spec: dependency-compatibility (adds numpy)

As an ML Engineer, I want scipy==1.17.1 declared in requirements.txt, pyproject.toml, and dependency_check.py so that the Spearman correlation baseline script can import scipy.stats.spearmanr.

**Acceptance Criteria**:
- [ ] scipy==1.17.1 appears in requirements.txt
- [ ] scipy==1.17.1 appears in pyproject.toml dependencies section
- [ ] scipy appears in infrastructure/dependency_check.py PACKAGE_IMPORT_MAP
- [ ] pip install scipy==1.17.1 works in the project environment (Python 3.14.3) — gating prerequisite; if it fails, escalate before proceeding

### US-2: Spearman correlation baseline
**Priority**: MUST
**Dependencies**: US-1 (scipy installed), reference dataset available

As an ML Engineer, I want to run `infrastructure/baselines/measure_spearman_baseline.py` on a reference dataset to capture pre-DSPy judge score agreement as a baseline Spearman correlation coefficient.

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/baselines/measure_spearman_baseline.py
- [ ] Script accepts --dataset argument: a single JSON file with two top-level keys `baseline_composites` (array of floats) and `adapter_composites` (array of floats), same length
- [ ] Script accepts --output path argument (defaults to baseline_results/spearman_judge_baseline.json)
- [ ] Script filters NaN values from both arrays before computation (preserves pairing by index)
- [ ] Script computes weighted composite scores using SCORING_WEIGHTS from src/audit/schema.py: ha_modernity(0.30), reasoning_depth(0.25), functionality(0.25), completeness(0.12), style(0.08) — applied to derive composites from raw judge_scores if input has judge_scores instead of pre-computed composites
- [ ] Script calls scipy.stats.spearmanr(baseline_composites, adapter_composites, method='auto') — relies on scipy 1.17.1 default auto-selection (exact for n<10, asymptotic for n>=10)
- [ ] Script handles n=0 after NaN filtering: returns rho=nan, p_value=nan, reason="no_valid_data"
- [ ] Script handles n=1 after NaN filtering: returns rho=nan, p_value=nan, reason="single_sample_undefined"
- [ ] Script handles n=2 after NaN filtering: returns rho=nan, p_value=nan, reason="insufficient_samples" (rho for 2 points is always ±1.0, meaningless for baseline)
- [ ] Script handles constant input: pre-checks len(set())<=1 BEFORE calling spearmanr; returns rho=0.0, p_value=1.0, reason="constant_input"
- [ ] Script outputs JSON in baseline result schema to baseline_results/spearman_judge_baseline.json
- [ ] Output includes: type, timestamp (ISO8601), score (float or string "uncomputable" for edge cases), details with p_value (float or string), n (int), method ("exact" or "asymptotic"), reason (string, present when edge case triggered), status ("ok" or edge case name)
- [ ] Script validates input JSON has expected fixture structure (baseline_composites and adapter_composites keys)
- [ ] Script exits 0 with valid JSON on success, exits 1 with clear error message on failure

### US-3: Calibration quality baseline
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want to run `infrastructure/baselines/run_calibration_baseline.py` to capture current calibration quality scores (coherence and LDI) as a baseline for future comparison.

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/baselines/run_calibration_baseline.py
- [ ] Script auto-detects data stage: if first result entry contains Stage 6 keys (parameter_effectiveness, coherence, etc.), treats as Stage 6; otherwise Stage 5. Logs the decision.
- [ ] Script captures mean coherence from calibration results: for Stage 6 data uses judge_scores["coherence"]; for Stage 5 data coherence is null (NOT derived from composite_score — mathematically impossible without individual dimension scores)
- [ ] Script sources LDI from pre-computed values in --ldi-source file (JSON or JSONL with "ldi" float field per record)
- [ ] Script accepts --dataset path argument (JSON file with "calibration_results" array or top-level array of records) and --output path argument
- [ ] Script accepts optional --ldi-source argument (JSON/JSONL file path; default: null)
- [ ] Script outputs JSON in baseline result schema to baseline_results/calibration_baseline.json
- [ ] Output includes: type, timestamp (ISO8601), score (mean_coherence or null), details with mean_coherence, mean_ldi, ldi_pass_rate, grid_config (from src/audit/calibration_schema.py CALIBRATION_GRID)
- [ ] ldi_pass_rate is computed from --ldi-source records only: count(ldi >= threshold) / total_records in --ldi-source. If --ldi-source unavailable, ldi_pass_rate is null.
- [ ] If LDI data is unavailable, outputs mean_ldi=null, ldi_pass_rate=null, logs warning, exits 0 (does not fail)
- [ ] If coherence data is unavailable, outputs mean_coherence=null, exits 0 (does not fail)
- [ ] Script exits 0 with valid JSON on success, exits 1 with clear error message on failure

### US-4: MIPROv2 compile baseline
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want to run `infrastructure/baselines/measure_mipro_compile_baseline.py` to establish a compile duration baseline for NFR-007 (MIPROv2 compile <= 3x baseline).

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/baselines/measure_mipro_compile_baseline.py
- [ ] Script reads grid configuration (CALIBRATION_GRID from src/audit/calibration_schema.py) and records profiles_tested = product of dimensions (4500)
- [ ] num_prompts priority: (1) --num-prompts CLI arg if provided, (2) prompt_count from CalibrationReport statistics if measured mode, (3) default of 6
- [ ] total_iterations = profiles_tested x num_prompts
- [ ] If an existing CalibrationReport JSON is available, extracts actual duration from statistics.execution_time_seconds (source: "measured"). If file is malformed, missing statistics, or execution_time_seconds is null, falls back to estimated mode with warning.
- [ ] If no CalibrationReport exists, computes estimated duration = total_iterations x avg_latency_seconds (default 0.5s — UNVERIFIED PLACEHOLDER, must be overridden with --avg-latency <measured_value>). source: "estimated"
- [ ] Script outputs JSON in baseline result schema to baseline_results/mipro_compile_baseline.json
- [ ] Output includes: type, timestamp (ISO8601), score (duration_seconds), details with grid_config, total_iterations, profiles_tested, source ("measured" or "estimated"), avg_latency_seconds
- [ ] Script exits 0 with valid JSON on success, exits 1 with clear error message on failure

### US-5: Rollback verification
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want a rollback verification script that confirms git revert operations complete in under 1 minute (NFR-009), so that the infrastructure layer is resilient to bad DSPy changes.

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/rollback_check.py
- [ ] Script creates a test commit in an isolated environment (temporary git worktree or cloned repo) to avoid affecting the developer's working tree
- [ ] Script performs git revert HEAD (reverts the test commit itself, NOT HEAD~1)
- [ ] Measures revert duration using time.perf_counter(), verifies < 60 seconds (NFR-009)
- [ ] Verifies git status is clean in the isolated environment only (no modified tracked files, no untracked files created by the script)
- [ ] Registers atexit handler to clean up isolated environment on normal exit; handles SIGINT/SIGTERM
- [ ] Returns exit code 0 if within target, 1 if exceeded
- [ ] Script exits 0 with clear message on success, exits 1 on failure

### US-6: Project structure and conventions
**Priority**: MUST
**Dependencies**: None

As a future maintainer, I want baseline scripts to follow project conventions (header checks, formatting, type checking) so they integrate seamlessly with existing CI tooling (check_headers, ruff, pyright).

**Acceptance Criteria**:
- [ ] All scripts include Apache-2.0 license header (3 tokens within first 4096 bytes: SPDX-License-Identifier:, Architect-Expert-Gap-Forge, Copyright)
- [ ] infrastructure/baselines/ directory includes __init__.py
- [ ] baseline_results/ directory is added to .gitignore. If directory already exists with tracked files, run `git rm -r --cached baseline_results/` to untrack them.
- [ ] All scripts pass `ruff format`
- [ ] All scripts pass pyright type checking
- [ ] All scripts support --dry-run flag: reads and validates input data, prints summary stats, exits 0 without writing output

---

## Implementation Conventions

The following conventions apply to all baseline scripts but are NOT user stories — they are enforcement concerns handled by CI tooling.

### CLI Pattern

Two patterns exist in the codebase. Scripts should choose based on purpose:

| Pattern | Reference | Usage |
|---------|-----------|-------|
| **Rich CLI** (typed main, _die(), logging.basicConfig, raise SystemExit(main())) | `infrastructure/dependency_check.py` | Scripts that need structured logging, testable argv injection, or are infrastructure tools |
| **Simple CLI** (argparse, sys.exit, print + sys.stderr) | `scripts/benchmark/compare_baseline.py` | Standalone benchmark scripts that produce human-readable output |

**Decision for this spec**: Use **Rich CLI pattern** for all `infrastructure/baselines/` scripts and `infrastructure/rollback_check.py` (they are infrastructure tools). The simple CLI pattern is reserved for `scripts/benchmark/` scripts.

**Rich CLI code skeleton**:
```python
from __future__ import annotations
import sys
import argparse
import logging

def _die(msg: str) -> "NoReturn":
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)
    parser = argparse.ArgumentParser()
    # ... add arguments ...
    args = parser.parse_args(argv)
    # ... do work ...
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### Shared Baseline Result Schema

All baseline scripts output JSON matching this schema:

```json
{
  "type": "spearman_baseline|calibration_baseline|mipro_compile",
  "timestamp": "ISO8601",
  "score": <float or string "uncomputable">,
  "details": {}
}
```

**Score semantics** (MUST check `type` before interpreting `score`):
- **Spearman**: `score` = rho (range -1 to 1, correlation coefficient). String "uncomputable" when edge case prevents computation.
- **Calibration**: `score` = `mean_coherence` (range 0-1). String "uncomputable" when no coherence data available.
- **MIPRO**: `score` = `duration_seconds` (wall-clock seconds, positive number). Lower is better.

Each script adds script-specific fields to `details`:

- **Spearman**: `p_value` (float or string "uncomputable"), `n` (int), `method` ("exact" or "asymptotic"), `status` ("ok" or edge case name), `reason` (string, present when edge case triggered)
- **Calibration**: `mean_coherence` (float or null), `mean_ldi` (float or null), `ldi_pass_rate` (float or null), `grid_config` (object from src/audit/calibration_schema.py CALIBRATION_GRID)
- **MIPRO Compile**: `grid_config` (object), `total_iterations` (int), `profiles_tested` (int), `source` ("measured" or "estimated"), `avg_latency_seconds` (float), `duration_seconds` (float, actual or estimated)

### Import Organization

```python
from __future__ import annotations   # ALWAYS first
import stdlib                         # alphabetical
from third_party                    # alphabetical
from src.module import ...           # local imports
```

### License Header

Within first 4096 bytes, must contain these 3 tokens (enforced by `scripts/check_headers.py`):
1. `SPDX-License-Identifier:`
2. `Architect-Expert-Gap-Forge`
3. `Copyright`

---

## Functional Requirements

### FR-001: scipy dependency declaration
- [FR-001.1] scipy==1.17.1 MUST be added to requirements.txt
- [FR-001.2] scipy MUST be added to pyproject.toml dependencies section
- [FR-001.3] scipy MUST be added to infrastructure/dependency_check.py PACKAGE_IMPORT_MAP
- [FR-001.4] numpy must already be present in requirements.txt (verified by dependency-compatibility spec completion)
- [FR-001.5] Before implementation begins, verify scipy==1.17.1 installs successfully on Python 3.14.3. If it fails, escalate (gating prerequisite).

### FR-002: Spearman baseline script
- [FR-002.1] Script MUST exist at infrastructure/baselines/measure_spearman_baseline.py
- [FR-002.2] Script MUST accept --dataset argument: a JSON file with two top-level keys `baseline_composites` (array of floats) and `adapter_composites` (array of floats), same length. If input has `judge_scores` instead of pre-computed composites, derives composites using SCORING_WEIGHTS.
- [FR-002.3] Script MUST accept --output path argument (default: baseline_results/spearman_judge_baseline.json)
- [FR-002.4] Script MUST import and use SCORING_WEIGHTS from src/audit/schema.py
- [FR-002.5] Script MUST compute composite score: sum(score[dim] * weight for dim, weight in SCORING_WEIGHTS.items()) if input has judge_scores
- [FR-002.6] Script MUST call scipy.stats.spearmanr(baseline_composites, adapter_composites, method='auto') — relies on scipy 1.17.1 default auto-selection
- [FR-002.7] Script MUST filter NaN values from both arrays before computation, preserving index pairing
- [FR-002.8] Script MUST handle n=0: returns structured error with status="no_valid_data", rho="uncomputable", p_value="uncomputable". Script MUST handle n=1: status="single_sample_undefined". Script MUST handle n=2: status="insufficient_samples", reason="rho for 2 points is always ±1.0 (perfect correlation), meaningless for baseline"
- [FR-002.9] Script MUST handle constant input: pre-checks len(set())<=1 BEFORE calling spearmanr; returns status="constant_input", rho=0.0, p_value=1.0
- [FR-002.10] Script MUST determine method="exact" for n<10, method="asymptotic" for n>=10 — this is implementation logic passed to scipy, not returned by scipy in its result
- [FR-002.11] Script MUST output JSON with type="spearman_baseline", timestamp (ISO8601), score (float for ok, string "uncomputable" for edge cases), details (p_value, n, method, status, reason)
- [FR-002.12] Script MUST validate input JSON has expected structure (baseline_composites and adapter_composites keys present) before processing
- [FR-002.13] Script MUST accept two top-level keys `baseline_composites` and `adapter_composites` in the dataset JSON, both arrays of equal length
- [FR-002.14] If only one data source available (only baseline or only adapter), exits with code 1 and clear error listing expected paired data

### FR-003: Calibration baseline script
- [FR-003.1] Script MUST exist at infrastructure/baselines/run_calibration_baseline.py
- [FR-003.2] Script MUST auto-detect data stage: if any result entry contains Stage 6 keys (parameter_effectiveness, coherence, parameter_alignment, task_completion, style), treats as Stage 6; otherwise treats as Stage 5. MUST log the decision.
- [FR-003.3] Script MUST capture mean coherence: for Stage 6 data, uses judge_scores["coherence"]; for Stage 5 data (like calibration_examples.json), coherence is NOT available and MUST output mean_coherence=null (Stage 5 dimensions are ha_modernity/reasoning_depth/functionality/completeness/style — coherence is exclusively a Stage 6 dimension)
- [FR-003.4] Script MUST source LDI from pre-computed values ONLY. MUST NOT compute LDI itself. Reads from --ldi-source file (JSON or JSONL where each record has "ldi" float field). If SampleRecord.ldi data available, uses that.
- [FR-003.5] Script MUST accept --dataset path argument (JSON file with "calibration_results" array or top-level array of records) and --output path argument
- [FR-003.6] Script MUST accept optional --ldi-source argument (JSON/JSONL file path; default: null) to specify LDI data file
- [FR-003.7] Script MUST output JSON with type="calibration_baseline", timestamp (ISO8601), score (mean_coherence or null, NOT composite), details (mean_coherence, mean_ldi, ldi_pass_rate, grid_config)
- [FR-003.8] Script MUST import CALIBRATION_GRID from src/audit/calibration_schema.py
- [FR-003.9] Script MUST import CALIBRATION_SCORING_WEIGHTS AND SCORING_WEIGHTS from src/audit/schema.py. Auto-detects stage and uses appropriate weight set for composite calculation.
- [FR-003.10] Composite score for calibration baseline: for Stage 6 data, sum(judge_scores[dim] * weight for dim, weight in CALIBRATION_SCORING_WEIGHTS.items()); for Stage 5 data, uses pre-computed composite_score from fixture (no recalculation). Output score field = mean_coherence.
- [FR-003.11] grid_config MUST include CALIBRATION_GRID from src/audit/calibration_schema.py (temperature, top_k, min_p, repetition_penalty, presence_penalty arrays with actual values). Sourced from schema, NOT from fixture data.
- [FR-003.12] ldi_pass_rate is the fraction of records in --ldi-source where LDI >= ldi_threshold. ldi_threshold configurable via --ldi-threshold argument (default: 0.01). ldi_pass_rate computed from --ldi-source records ONLY, NOT from --dataset.
- [FR-003.13] If LDI data is unavailable (no --ldi-source given or file not found or unparseable): output mean_ldi=null, ldi_pass_rate=null, log a warning, and exit 0 (does not fail)
- [FR-003.14] If coherence data is unavailable: output mean_coherence=null, exit 0 (does not fail)

### FR-004: MIPROv2 compile baseline script
- [FR-004.1] Script MUST exist at infrastructure/baselines/measure_mipro_compile_baseline.py
- [FR-004.2] Script MUST read grid configuration (CALIBRATION_GRID from src/audit/calibration_schema.py) and compute profiles_tested = product of dimensions (4500)
- [FR-004.3] num_prompts priority: (1) --num-prompts CLI arg if provided, (2) prompt_count from CalibrationReport statistics if measured mode, (3) default 6. total_iterations = profiles_tested x num_prompts
- [FR-004.4] If an existing CalibrationReport JSON is available, extracts actual duration from statistics.execution_time_seconds (source: "measured")
- [FR-004.5] If CalibrationReport exists but is malformed, missing statistics key, or execution_time_seconds is null: treats as "no report available", logs warning, falls back to estimated mode
- [FR-004.6] If no CalibrationReport exists, computes estimated duration = total_iterations x avg_latency_seconds (default 0.5s, UNVERIFIED PLACEHOLDER, configurable via --avg-latency). NOT an actual grid execution. (source: "estimated")
- [FR-004.7] Script MUST output JSON with type="mipro_compile", timestamp (ISO8601), score (duration_seconds), details (grid_config, profiles_tested, total_iterations, source, avg_latency_seconds)
- [FR-004.8] Script MUST accept optional --num-prompts argument (default: 6) and --avg-latency argument (default: 0.5, documented as unverified placeholder)

### FR-005: Rollback verification script
- [FR-005.1] Script MUST exist at infrastructure/rollback_check.py
- [FR-005.2] Script MUST create a test commit (git add + git commit) in an isolated environment (temporary git worktree or cloned repo) to avoid affecting the developer's working tree
- [FR-005.3] Script MUST measure git revert HEAD duration using time.perf_counter() — reverts the test commit itself (HEAD), not a prior commit (HEAD~1). The "clean working tree" check applies only to the isolated environment.
- [FR-005.4] Script MUST verify < 60 second threshold (NFR-009)
- [FR-005.5] Script MUST verify git status is clean in the isolated environment only: no modified tracked files, no untracked files created by the script, no staged changes
- [FR-005.6] Script MUST return exit code 0 if within target, 1 if exceeded
- [FR-005.7] Script MUST clean up the isolated environment (remove temporary worktree/clone) after verification
- [FR-005.8] Script MUST register atexit handler to clean up isolated environment on normal exit. MUST handle SIGINT and SIGTERM signals for cleanup. Errors during cleanup are non-fatal.

### FR-006: Project structure
- [FR-006.1] infrastructure/baselines/ directory MUST be created with __init__.py
- [FR-006.2] baseline_results/ directory MUST be created at project root
- [FR-006.3] baseline_results/ MUST be added to .gitignore (runtime data, not source control) — line: `baseline_results/`. If directory already exists with tracked files, run `git rm -r --cached baseline_results/` to untrack.
- [FR-006.4] All scripts MUST follow Rich CLI pattern (dependency_check.py style): typed main returning int, _die(), logging.basicConfig, raise SystemExit(main())
- [FR-006.5] All scripts MUST pass ruff format
- [FR-006.6] All scripts MUST pass pyright type checking
- [FR-006.7] All scripts MUST include Apache-2.0 license header (3 tokens within first 4096 bytes)
- [FR-006.8] All scripts MUST write output files atomically: write to `<output>.tmp` then `os.rename(tmp, output)`. After rename, call os.fsync() on the output file. Scripts MUST be idempotent — re-running with the same inputs produces the same score and details (timestamp may differ).
- [FR-006.9] All scripts MUST support --dry-run flag: reads and validates input data, prints summary stats, exits 0 without writing output file.
- [FR-006.10] All scripts that import from src/ MUST prepend project root to sys.path: `sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))`. MUST create output directory if missing: `os.makedirs(os.path.dirname(output), exist_ok=True)`.

---

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-001 | Spearman baseline performance | script runtime | < 10 seconds (reads pre-computed scores, no live API) |
| NFR-002 | Spearman correlation target | rho > threshold | > 0.8 with existing judge.py scores |
| NFR-003 | Calibration baseline performance | script runtime | < 1 minute (reads pre-existing data only, curation pipeline is out of scope) |
| NFR-004 | MIPROv2 compile baseline performance | script runtime | < 1 minute (reads config or extracts from existing report, no actual grid execution) |
| NFR-005 | Rollback time | git revert duration | < 60 seconds |
| NFR-006 | Rollback isolation | no main repo modification | Test commit/revert confined to temporary worktree or clone |
| NFR-007 | MIPROv2 compile duration ceiling | compile_time <= 3x baseline | baseline measured by this spec |
| NFR-008 | Baseline output integrity | file write safety | Atomic writes (write to temp file, then fsync + rename) to prevent corruption on interrupt. Idempotent: same inputs produce same score/details (timestamp may differ). |

---

## Glossary

| Term | Definition |
|------|-----------|
| **SCORING_WEIGHTS** | Stage 5 judge dimension weights (`src/audit/schema.py:39-45`): ha_modernity(0.30), reasoning_depth(0.25), functionality(0.25), completeness(0.12), style(0.08) |
| **CALIBRATION_SCORING_WEIGHTS** | Stage 6 judge dimension weights (`src/audit/schema.py:49-55`): parameter_effectiveness(0.30), task_completion(0.20), parameter_alignment(0.25), coherence(0.15), style(0.10) |
| **LDI** | Length Density Index — curation/factory pipeline quality filter, NOT a calibration scoring dimension. Factory LDI: K=1200, character-level. Curation LDI: K=800, token-level |
| **judge_scores** | Per-result scores dict (stage-specific keys): Stage 5 uses ha_modernity/reasoning_depth/functionality/completeness/style; Stage 6 uses parameter_effectiveness/task_completion/parameter_alignment/coherence/style |
| **composite_score** | Weighted aggregation of judge_scores: `sum(score[dim] * weight for dim, weight in weights.items())`. Pre-computed in fixtures as `composite_score` field. |
| **NormalizedJudgeResponse** | TypedDict with baseline dict[str, float], adapter dict[str, float], reasoning str (`src/audit/schema.py:81`) |
| **MIPROv2** | DSPy's automated prompt/Signature optimization algorithm. Compiles externalized prompts into optimized signatures using a training dataset. |
| **Calibration grid** | 4,500 profile configurations × 6 prompts = 27,000 total iterations (`src/audit/calibration_schema.py:66-72`) |
| **CalibrationReport** | Frozen dataclass (`src/audit/calibration_schema.py:209-251`) with timestamp, total_iterations, best_profile, statistics |
| **CALIBRATION_GRID** | Parameter grid from `src/audit/calibration_schema.py:66-72`: temperature [0.3, 0.5, 0.6, 0.7, 0.9, 1.1], top_k [5, 10, 20, 40, 60, 80], min_p [0.0, 0.02, 0.05, 0.1, 0.15], repetition_penalty [1.0, 1.05, 1.1, 1.15, 1.2], presence_penalty [0.0, 0.5, 1.0, 1.5, 2.0] |
| **baseline_results/** | Output directory at project root for baseline JSON files. Added to .gitignore. |
| **infrastructure/baselines/** | Directory for baseline measurement scripts (created by this spec). |
| **judge.py** | `/src/audit/judge.py` — main judge scoring module that produces judge_scores and composite_score |
| **CalibrationResult** | Dataclass with profile, exam_id, judge_scores, composite_score, adjusted_score (`src/audit/calibration_schema.py`) |
| **SampleRecord.ldi** | Float field in `src/audit/schema.py:129` storing LDI for individual records |
| **ldi_pass_rate** | Fraction of records in --ldi-source where LDI >= ldi_threshold (default 0.01) |
| **NFR-002** | Spearman correlation > 0.8 target for DSPy improvement assessment |
| **NFR-006** | Rollback must be confined to isolated environment (temporary worktree/clone) |
| **NFR-007** | MIPROv2 compile duration <= 3x baseline measured by this spec |
| **NFR-008** | Baseline outputs written atomically; idempotent (same inputs → same score/details) |

---

## Out of Scope

- DSPy implementation or optimization (covered by Epic 1: aegf-dspy-integration)
- Running the curation pipeline (baseline reads existing curation outputs, does not trigger curation)
- Implementing or running grid search (baseline MEASURES/ESTIMATES existing calibration duration from config or existing reports, NOT from actual grid execution)
- Test suite (tests added in Epic 1)
- CI/CD integration for baseline comparisons
- Historical baseline trend analysis or dashboards

---

## Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| Spec: dependency-compatibility | Completed | Added numpy but scipy gap was discovered during this spec's research. scipy==1.17.1 declaration is WITHIN this spec's scope (FR-001). |
| Spec: prompt-externalization | Completed | Provides .example.yaml reference patterns |
| src/audit/schema.py | Available | SCORING_WEIGHTS, CALIBRATION_SCORING_WEIGHTS, NormalizedJudgeResponse |
| src/audit/scorecard.py | Available | _composite function pattern |
| src/audit/calibration_schema.py | Available | CalibrationReport, CALIBRATION_GRID |
| src/factory/ldi_validator.py | Available | Factory LDI pattern (micro-snippet exception threshold) |
| src/curation/quality_filter.py | Available | Curation LDI pattern |
| tests/fixtures/calibration_examples.json | Available | 4 calibration_results entries with Stage 5 judge_scores + composite_score. 5 sample_prompts. NOT sufficient for Spearman (needs paired baseline+adapter scores). |
| tests/fixtures/judge_scoring_response.json | Available | Full judge output (reference) |
| tests/fixtures/inference_results.json | Available | baseline + adapter responses (text, NOT scores) |
| scripts/benchmark/compare_baseline.py | Available | Simple CLI pattern reference (224 lines) |
| infrastructure/dependency_check.py | Available | Rich CLI pattern reference (274 lines) |

---

## Success Criteria

- [ ] All 4 baseline scripts exist and can be executed manually against test fixtures without errors (pytest test suite is out of scope per Out of Scope)
- [ ] baseline_results/ contains valid JSON output from each script matching the shared schema (type, timestamp, score, details)
- [ ] scipy==1.17.1 is importable in the project Python 3.14.3 environment (`python -c 'import scipy'` succeeds)
- [ ] Spearman baseline produces a rho value (or edge case status) from paired baseline/adapter composite data (validates measurement approach)
- [ ] Calibration baseline captures mean_coherence (null for Stage 5 data) and mean_ldi (null if --ldi-source unavailable)
- [ ] MIPROv2 baseline captures duration (measured or estimated) with correct grid_config and profiles_tested=4500
- [ ] Rollback verification confirms git revert < 60 seconds in isolated environment
- [ ] All scripts pass ruff format and pyright type checking
- [ ] All scripts support --dry-run flag for pre-flight validation
- [ ] baseline_results/ is added to .gitignore (and any existing tracked files are untracked)

---

## Verification Contract

**Project type**: `cli-tool`

This spec creates CLI scripts in `infrastructure/baselines/` that read data from existing fixtures. No HTTP server, no browser UI, no API endpoints. Scripts call scipy (local computation) and import from src/ (local imports).

**Entry points**:
- CLI: `python infrastructure/baselines/measure_spearman_baseline.py --dataset <path> --output <path>`
- CLI: `python infrastructure/baselines/run_calibration_baseline.py --dataset <path> --output <path>`
- CLI: `python infrastructure/baselines/measure_mipro_compile_baseline.py --dataset <path> --output <path>`
- CLI: `python infrastructure/rollback_check.py`
- File reads: `tests/fixtures/calibration_examples.json`, `tests/fixtures/judge_scoring_response.json`, `tests/fixtures/inference_results.json`
- Import: `src/audit/schema.py` (SCORING_WEIGHTS), `src/audit/calibration_schema.py` (CALIBRATION_GRID)

**Observable signals**:
- PASS: Script exits with code 0, output JSON file exists, JSON has type/timestamp/score/details fields
- FAIL: Script exits with code 1, stderr contains error, output file missing or malformed JSON
- Spearman PASS: Script exits 0 with valid JSON. Score is a float (rho) for ok status, or string "uncomputable" for edge cases. If dataset has > 3 entries with paired data, rho is a valid correlation.
- Calibration PASS: `calibration_baseline.json` has score = mean_coherence (float or null). mean_ldi present (float or null if --ldi-source unavailable).
- Rollback PASS: revert completes in < 60s, git status clean in isolated environment, isolated environment cleaned up

**Hard invariants**:
- Auth/session: not applicable (local scripts)
- Data integrity: baseline output JSON must not corrupt existing fixtures
- Import safety: scripts must not modify `src/audit/schema.py` or `src/audit/calibration_schema.py`
- Adjacent flows: scipy installation must not break existing imports in `src/` or `scripts/`
- Atomic writes: all output files must be written atomically (temp file + rename) to prevent corruption on interrupt

**Seed data**:
- `tests/fixtures/calibration_examples.json`: 4 entries with composite_score (Stage 5). Use for Spearman baseline composite scores.
- `tests/fixtures/judge_scoring_response.json`: full judge output (reference)
- `src/audit/schema.py`: SCORING_WEIGHTS constant (required import)
- `src/audit/calibration_schema.py`: CALIBRATION_GRID constant (required import for calibration/mipro baselines)

**Dependency map**:
- `dependency-compatibility` spec: shares requirements.txt and pyproject.toml for scipy declaration
- `src/audit/schema.py`: read-only import (SCORING_WEIGHTS)
- `src/audit/calibration_schema.py`: read-only import (CALIBRATION_GRID)
- `scripts/benchmark/compare_baseline.py`: pattern reference only (not imported)
- `infrastructure/dependency_check.py`: pattern reference only (not imported)

**Escalate if**:
- scipy==1.17.1 fails to install on Python 3.14.3 in the project environment
- No fixture data with composite_score or judge_scores is available for Spearman baseline
- dependency-compatibility spec has not added numpy to requirements.txt (blocks scipy installation on Python 3.14 due to numpy dependency)
- Grid search configuration (CALIBRATION_GRID) has changed since research — verify against live code

---

## Next Steps

1. [PREREQ] Verify dependency-compatibility spec PR is merged and numpy is in requirements.txt
2. [PREREQ] Verify scipy==1.17.1 installs on Python 3.14.3 (`pip install scipy==1.17.1`)
3. [FR-001] Add scipy==1.17.1 to requirements.txt, pyproject.toml, and infrastructure/dependency_check.py
4. Create `infrastructure/baselines/` directory with `__init__.py`
5. Create `baseline_results/` directory at project root
6. Add `baseline_results/` to `.gitignore` (untrack any existing tracked files)
7. Implement `measure_spearman_baseline.py` — NOTE: requires paired baseline+adapter composite scores (calibration_examples.json has composite_score only, not paired)
8. Implement `run_calibration_baseline.py` — NOTE: calibration_examples.json is Stage 5 data (coherence will be null)
9. Implement `measure_mipro_compile_baseline.py`
10. Implement `rollback_check.py`
11. Run all scripts with `--dry-run` against test fixtures and verify output schema
12. Run `ruff format` + `pyright` on all new scripts
13. Commit and push

---

## Sources

- `specs/baseline-measurement/plan.md` — Acceptance criteria, interface contracts, baseline result schema
- `specs/baseline-measurement/research.md` — Scoring weights, LDI analysis, dependency analysis, scipy wheel verification
- `specs/_epics/aegf-infrastructure/epic.md` — Story 0.1, NFR-002/007/009
- `specs/dependency-compatibility/research.md` — scipy gap discovered during this spec research
- `_bmad-output/planning-artifacts/epics.md` — BMAD Story 0.1
- `scripts/benchmark/compare_baseline.py` — Simple CLI pattern reference (224 lines)
- `infrastructure/dependency_check.py` — Rich CLI pattern reference (274 lines)
- `src/audit/schema.py` — SCORING_WEIGHTS, CALIBRATION_SCORING_WEIGHTS, NormalizedJudgeResponse
- `src/audit/scorecard.py` — _composite function pattern
- `src/audit/calibration_schema.py` — CalibrationReport, CALIBRATION_GRID
- `src/factory/ldi_validator.py` — Factory LDI implementation (micro-snippet exception threshold)
- `src/curation/quality_filter.py` — Curation LDI implementation
- `tests/fixtures/calibration_examples.json` — 4 calibration_results with Stage 5 judge_scores and composite_score
