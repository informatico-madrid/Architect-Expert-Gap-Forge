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
- [ ] Script accepts --dataset path argument (reads composite scores from fixture JSON or calibration results JSON)
- [ ] Script accepts --output path argument (defaults to baseline_results/spearman_judge_baseline.json)
- [ ] Script filters NaN values from input data before computation
- [ ] Script computes weighted composite scores using SCORING_WEIGHTS from src/audit/schema.py: ha_modernity(0.30), reasoning_depth(0.25), functionality(0.25), completeness(0.12), style(0.08)
- [ ] Script computes scipy.stats.spearmanr between baseline and adapter composites
- [ ] Script handles n<3 edge case (returns structured error with reason="insufficient_samples", rho=nan, p_value=nan) — rho for 2 points is always ±1.0 (perfect correlation), which is meaningless for baseline assessment
- [ ] Script handles constant input edge case (detect via len(set())<=1, returns rho=0.0, p_value=1.0, reason="constant_input") — catches ValueError raised by scipy for constant input
- [ ] Script outputs JSON in baseline result schema to baseline_results/spearman_judge_baseline.json
- [ ] Script determines method="exact" for n<10, method="asymptotic" for n>=10 (this is implementation logic, not returned by scipy)
- [ ] Output includes: type, timestamp (ISO8601), score (rho float), details with p_value, n, method (exact/asymptotic), reason (string, present when an edge case is triggered)
- [ ] Script validates input JSON has expected fixture structure (composite_score or judge_scores keys present)
- [ ] Script exits 0 with valid JSON on success, exits 1 with clear error message on failure

### US-3: Calibration quality baseline
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want to run `infrastructure/baselines/run_calibration_baseline.py` to capture current calibration quality scores (coherence and LDI) as a baseline for future comparison.

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/baselines/run_calibration_baseline.py
- [ ] Script captures mean coherence from calibration results (judge_scores["coherence"] for Stage 6, or derives from composite_score for Stage 5 data)
- [ ] Script sources LDI from curation pipeline outputs or SampleRecord.ldi (NOT from calibration results)
- [ ] Script accepts --dataset path argument and --output path argument
- [ ] Script accepts optional --ldi-source argument (default: null; if curation LDI data unavailable, outputs mean_ldi=null with warning log)
- [ ] Script outputs JSON in baseline result schema to baseline_results/calibration_baseline.json
- [ ] Output includes: type, timestamp (ISO8601), score (float composite), details with mean_coherence, mean_ldi, ldi_pass_rate, grid_config, total_iterations
- [ ] If LDI data is unavailable, outputs mean_ldi=null with a warning log (does not fail)
- [ ] If coherence data is unavailable, outputs mean_coherence=null (does not fail)
- [ ] Script exits 0 with valid JSON on success, exits 1 with clear error message on failure

### US-4: MIPROv2 compile baseline
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want to run `infrastructure/baselines/measure_mipro_compile_baseline.py` to establish a compile duration baseline for NFR-007 (MIPROv2 compile <= 3x baseline).

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/baselines/measure_mipro_compile_baseline.py
- [ ] Script reads grid configuration (CALIBRATION_GRID from src/audit/calibration_schema.py) and records total_iterations = profiles x prompts
- [ ] If an existing CalibrationReport JSON is available, script extracts actual duration from statistics.execution_time_seconds
- [ ] If no CalibrationReport exists, script computes estimated duration = total_iterations x avg_latency (default 0.5s per inference call — configurable via --avg-latency argument)
- [ ] Script outputs JSON in baseline result schema to baseline_results/mipro_compile_baseline.json
- [ ] Output includes: type, timestamp (ISO8601), score (duration_seconds), details with grid_config, total_iterations, profiles_tested, source ("measured" or "estimated")
- [ ] Script exits 0 with valid JSON on success, exits 1 with clear error message on failure

### US-5: Rollback verification
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want a rollback verification script that confirms git revert operations complete in under 1 minute (NFR-009), so that the infrastructure layer is resilient to bad DSPy changes.

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/rollback_check.py
- [ ] Script creates a test commit, performs git revert HEAD~1
- [ ] Measures revert duration, verifies < 60 seconds (NFR-009)
- [ ] Verifies git status is clean after revert (no untracked or modified files)
- [ ] Returns exit code 0 if within target, 1 if exceeded
- [ ] Script exits 0 with clear message on success, exits 1 on failure

### US-6: Project structure and conventions
**Priority**: MUST
**Dependencies**: None

As a future maintainer, I want baseline scripts to follow project conventions (header checks, formatting, type checking) so they integrate seamlessly with existing CI tooling (check_headers, ruff, pyright).

**Acceptance Criteria**:
- [ ] All scripts include Apache-2.0 license header (3 tokens within first 4096 bytes: SPDX-License-Identifier:, Architect-Expert-Gap-Forge, Copyright)
- [ ] infrastructure/baselines/ directory includes __init__.py
- [ ] baseline_results/ directory is added to .gitignore
- [ ] All scripts pass `ruff format`
- [ ] All scripts pass pyright type checking

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

### Shared Baseline Result Schema

All baseline scripts output JSON matching this schema:

```json
{
  "type": "spearman_baseline|calibration_baseline|mipro_compile",
  "timestamp": "ISO8601",
  "score": <float>,
  "details": {}
}
```

Each script adds script-specific fields to `details`:

- **Spearman**: `p_value` (float), `n` (int), `method` ("exact" or "asymptotic"), `pass_target` (bool)
- **Calibration**: `mean_coherence` (float), `mean_ldi` (float or null), `ldi_pass_rate` (float or null), `grid_config` (object), `total_iterations` (int)
- **MIPRO Compile**: `grid_config` (object), `total_iterations` (int), `profiles_tested` (int), `source` ("measured" or "estimated"), `avg_latency_seconds` (float)

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
- [FR-002.2] Script MUST accept --dataset path argument (reads composite scores from fixture JSON or calibration results JSON)
- [FR-002.3] Script MUST accept --output path argument (default: baseline_results/spearman_judge_baseline.json)
- [FR-002.4] Script MUST import and use SCORING_WEIGHTS from src/audit/schema.py
- [FR-002.5] Script MUST compute composite score: sum(score * weight for each dimension)
- [FR-002.6] Script MUST call scipy.stats.spearmanr(baseline_composites, adapter_composites)
- [FR-002.7] Script MUST filter NaN values from input data before computation
- [FR-002.8] Script MUST handle n<3 edge case (return structured error with reason="insufficient_samples", p_value=nan, rho=nan) — rho for 2 points is always ±1.0 (perfect correlation), which is meaningless for baseline assessment
- [FR-002.9] Script MUST handle constant input edge case (detect via len(set())<=1, catch ValueError from scipy, return rho=0.0, p_value=1.0, reason="constant_input")
- [FR-002.10] Script MUST determine method="exact" for n<10, method="asymptotic" for n>=10 (implementation logic — scipy does not return this in its result)
- [FR-002.11] Script MUST output JSON with type="spearman_baseline", timestamp (ISO8601), score (rho float), details (p_value, n, method, reason)
- [FR-002.12] Script MUST validate input JSON has expected structure (composite_score or judge_scores keys present) before processing
- [FR-002.13] Script MUST check for fixture/file availability before running; if no valid input data is found, exit with code 1 and a list of available fixtures

### FR-003: Calibration baseline script
- [FR-003.1] Script MUST exist at infrastructure/baselines/run_calibration_baseline.py
- [FR-003.2] Script MUST capture mean coherence from calibration results: for Stage 6 data use judge_scores["coherence"]; for Stage 5 data (like calibration_examples.json) coherence is NOT available and MUST output mean_coherence=null (Stage 5 dimensions are ha_modernity/reasoning_depth/functionality/completeness/style — coherence is exclusively a Stage 6 dimension)
- [FR-003.3] Script MUST source LDI from curation pipeline outputs or SampleRecord.ldi (NOT from calibration results)
- [FR-003.4] Script MUST accept --dataset path argument and --output path argument
- [FR-003.5] Script MUST accept optional --ldi-source argument (default: null) to specify LDI data file path
- [FR-003.6] Script MUST output JSON with type="calibration_baseline", timestamp (ISO8601), score (float composite), details (mean_coherence, mean_ldi, ldi_pass_rate, grid_config, total_iterations)
- [FR-003.7] Script MUST import CALIBRATION_GRID from src/audit/calibration_schema.py
- [FR-003.8] Script MUST import CALIBRATION_SCORING_WEIGHTS from src/audit/schema.py
- [FR-003.9] Composite score for calibration baseline: for Stage 6 data, sum(judge_scores[dim] * weight for dim, weight in CALIBRATION_SCORING_WEIGHTS.items()); for Stage 5 data (like calibration_examples.json), use the pre-computed composite_score from the fixture directly (no recalculation)
- [FR-003.10] grid_config MUST include CALIBRATION_GRID from src/audit/calibration_schema.py (temperature, top_k, min_p, repetition_penalty, presence_penalty arrays with actual values)
- [FR-003.11] ldi_pass_rate is the fraction of records where LDI >= ldi_threshold, where ldi_threshold is configurable via --ldi-threshold argument (default: 0.01, from micro-snippet exception threshold in src/factory/ldi_validator.py)
- [FR-003.12] If LDI data is unavailable (no --ldi-source given or file not found): output mean_ldi=null, ldi_pass_rate=null, log a warning, and exit 0 (does not fail)
- [FR-003.13] If coherence data is unavailable: output mean_coherence=null, exit 0 (does not fail)

### FR-004: MIPROv2 compile baseline script
- [FR-004.1] Script MUST exist at infrastructure/baselines/measure_mipro_compile_baseline.py
- [FR-004.2] Script MUST read grid configuration (CALIBRATION_GRID from src/audit/calibration_schema.py)
- [FR-004.3] Script MUST record profiles_tested = product of CALIBRATION_GRID dimensions (4500) and total_iterations = profiles_tested x num_prompts (default num_prompts=6, configurable via --num-prompts)
- [FR-004.4] If an existing CalibrationReport JSON is available, script extracts actual duration from statistics.execution_time_seconds (source: "measured")
- [FR-004.5] If no CalibrationReport exists, script computes estimated duration = total_iterations x avg_latency_seconds (default 0.5s, configurable via --avg-latency). This is NOT an actual grid execution. (source: "estimated")
- [FR-004.6] Script MUST output JSON with type="mipro_compile", timestamp (ISO8601), score (duration_seconds), details (grid_config, profiles_tested, total_iterations, source, avg_latency_seconds)
- [FR-004.7] Script MUST accept optional --num-prompts argument (default: 6) and --avg-latency argument (default: 0.5)

### FR-005: Rollback verification script
- [FR-005.1] Script MUST exist at infrastructure/rollback_check.py
- [FR-005.2] Script MUST create a test commit (git add + git commit) in an isolated environment (e.g., temporary git worktree or cloned repo) to avoid affecting the developer's working tree
- [FR-005.3] Script MUST measure git revert HEAD duration using time.perf_counter() — reverts the test commit itself (HEAD), not a prior commit (HEAD~1)
- [FR-005.4] Script MUST verify < 60 second threshold (NFR-009)
- [FR-005.5] Script MUST verify git status is clean after revert (no modified or untracked files)
- [FR-005.6] Script MUST return exit code 0 if within target, 1 if exceeded
- [FR-005.7] Script MUST clean up the isolated environment (remove temporary worktree/clone) after verification

### FR-006: Project structure
- [FR-006.1] infrastructure/baselines/ directory MUST be created with __init__.py
- [FR-006.2] baseline_results/ directory MUST be created at project root
- [FR-006.3] baseline_results/ MUST be added to .gitignore (runtime data, not source control) — line: `baseline_results/`
- [FR-006.4] All scripts MUST follow Rich CLI pattern (dependency_check.py style): typed main returning int, _die(), logging.basicConfig, raise SystemExit(main())
- [FR-006.5] All scripts MUST pass ruff format
- [FR-006.6] All scripts MUST pass pyright type checking
- [FR-006.7] All scripts MUST include Apache-2.0 license header (3 tokens within first 4096 bytes)
- [FR-006.8] All scripts MUST write output files atomically: write to `<output>.tmp` then `os.rename(tmp, output)`. Scripts MUST be idempotent — re-running with the same inputs produces the same output without corruption.

---

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-001 | Spearman baseline performance | script runtime | < 5 minutes (reads pre-computed scores, no live API) |
| NFR-002 | Spearman correlation target | rho > threshold | > 0.8 with existing judge.py scores |
| NFR-003 | Calibration baseline performance | script runtime | < 1 minute (reads pre-existing data only, curation pipeline is out of scope) |
| NFR-004 | MIPROv2 compile baseline performance | script runtime | < 1 minute (reads config or extracts from existing report, no actual grid execution) |
| NFR-005 | Rollback time | git revert duration | < 60 seconds |
| NFR-007 | MIPROv2 compile duration ceiling | compile_time <= 3x baseline | baseline measured by this spec |
| NFR-008 | Baseline output integrity | file write safety | Atomic writes (write to temp file, then rename) to prevent corruption on interrupt. Scripts MUST be idempotent. |
| NFR-010 | Code quality | ruff format + pyright | All baseline scripts pass |

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
| **NFR-002** | Spearman correlation > 0.8 target for DSPy improvement assessment |
| **NFR-007** | MIPROv2 compile duration <= 3x baseline measured by this spec |
| **NFR-009** | Rollback via git revert must complete in < 60 seconds |
| **Calibration grid** | 4,500 profile configurations × 6 prompts = 27,000 total iterations (`src/audit/calibration_schema.py:66-72`) |
| **CalibrationReport** | Frozen dataclass (`src/audit/calibration_schema.py:209-251`) with timestamp, total_iterations, best_profile, statistics |
| **CALIBRATION_GRID** | Parameter grid from `src/audit/calibration_schema.py:66-72`: temperature [0.3, 0.5, 0.6, 0.7, 0.9, 1.1], top_k [5, 10, 20, 40, 60, 80], min_p [0.0, 0.02, 0.05, 0.1, 0.15], repetition_penalty [1.0, 1.05, 1.1, 1.15, 1.2], presence_penalty [0.0, 0.5, 1.0, 1.5, 2.0] |
| **baseline_results/** | Output directory at project root for baseline JSON files. Added to .gitignore. |
| **infrastructure/baselines/** | Directory for baseline measurement scripts (created by this spec). |
| **judge.py** | `/src/audit/judge.py` — main judge scoring module that produces judge_scores and composite_score |
| **CalibrationResult** | Dataclass with profile, exam_id, judge_scores, composite_score, adjusted_score (`src/audit/calibration_schema.py`) |
| **SampleRecord.ldi** | Float field in `src/audit/schema.py:129` storing LDI for individual records |
| **ldi_pass_rate** | Fraction of records where LDI >= 0.01 (micro-snippet exception threshold from `src/factory/ldi_validator.py`) |

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
| Spec: dependency-compatibility | Completed (but MISSED scipy) | Adds scipy==1.17.1 to requirements.txt as part of this spec. Verify PR is merged before implementing US-1. |
| Spec: prompt-externalization | Completed | Provides .example.yaml reference patterns |
| src/audit/schema.py | Available | SCORING_WEIGHTS, CALIBRATION_SCORING_WEIGHTS, NormalizedJudgeResponse |
| src/audit/scorecard.py | Available | _composite function pattern |
| src/audit/calibration_schema.py | Available | CalibrationReport, CALIBRATION_GRID |
| src/factory/ldi_validator.py | Available | Factory LDI pattern |
| src/curation/quality_filter.py | Available | Curation LDI pattern |
| tests/fixtures/calibration_examples.json | Available | 4 calibration_results entries with Stage 5 judge_scores + composite_score. 5 sample_prompts. |
| tests/fixtures/judge_scoring_response.json | Available | Full judge output |
| tests/fixtures/inference_results.json | Available | baseline + adapter responses |
| scripts/benchmark/compare_baseline.py | Available | Simple CLI pattern reference (224 lines) |
| infrastructure/dependency_check.py | Available | Rich CLI pattern reference (274 lines) |

---

## Success Criteria

- [ ] All 4 baseline scripts exist and run without errors against test fixtures
- [ ] baseline_results/ contains valid JSON output from each script matching the shared schema (type, timestamp, score, details)
- [ ] scipy==1.17.1 is declared in all required locations and installs on Python 3.14.3
- [ ] Spearman baseline produces a rho value from existing calibration_examples.json fixture (validates measurement approach)
- [ ] Calibration baseline captures mean_coherence and mean_ldi (or null with warning) from available data
- [ ] MIPROv2 baseline captures duration (measured or estimated) with correct grid_config and total_iterations=27000
- [ ] Rollback verification confirms git revert < 60 seconds
- [ ] All scripts pass ruff format and pyright type checking
- [ ] baseline_results/ is added to .gitignore

---

## Verification Contract

**Project type**: `api-only`

This spec creates `infrastructure/baselines/` scripts that read data from existing fixtures and API outputs. There is no browser UI. The scripts call scipy (local computation) and potentially the calibration infrastructure (local imports). No HTTP server is required.

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
- Spearman PASS: `spearman_judge_baseline.json` has score > 0.8 (if dataset has > 3 entries)
- Calibration PASS: `calibration_baseline.json` has mean_coherence and mean_ldi (or null if unavailable)
- Rollback PASS: revert completes in < 60s, git status shows clean working tree

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
3. Create `infrastructure/baselines/` directory with `__init__.py`
4. Create `baseline_results/` directory at project root
5. Add `baseline_results/` to `.gitignore`
6. Implement `measure_spearman_baseline.py`
7. Implement `run_calibration_baseline.py`
8. Implement `measure_mipro_compile_baseline.py`
9. Implement `rollback_check.py`
10. Run all scripts against `tests/fixtures/calibration_examples.json` and verify output schema
11. Run `ruff format` + `pyright` on all new scripts
12. Commit and push

---

## Sources

- `specs/baseline-measurement/plan.md` — Acceptance criteria, interface contracts, baseline result schema
- `specs/baseline-measurement/research.md` — Scoring weights, LDI analysis, dependency analysis, scipy wheel verification
- `specs/_epics/aegf-infrastructure/epic.md` — Story 0.1, NFR-002/007/009
- `specs/_epics/aegf-dspy-integration/README.md` — 7 source bug corrections from prompt-externalization
- `specs/dependency-compatibility/research.md` — scipy gap discovered during this spec research
- `_bmad-output/planning-artifacts/epics.md` — BMAD Story 0.1
- `scripts/benchmark/compare_baseline.py` — Simple CLI pattern reference (224 lines)
- `infrastructure/dependency_check.py` — Rich CLI pattern reference (274 lines)
- `src/audit/schema.py` — SCORING_WEIGHTS, CALIBRATION_SCORING_WEIGHTS, NormalizedJudgeResponse
- `src/audit/scorecard.py` — _composite function pattern
- `src/audit/calibration_schema.py` — CalibrationReport, CALIBRATION_GRID
- `src/factory/ldi_validator.py` — Factory LDI implementation
- `src/curation/quality_filter.py` — Curation LDI implementation
- `src/utils/logging.py` — get_logger with RichHandler
- `src/utils/exceptions.py` — Custom exception classes
- `tests/fixtures/calibration_examples.json` — 4 calibration_results with Stage 5 judge_scores and composite_score
