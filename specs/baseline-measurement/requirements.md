# Requirements: Baseline Measurement

**Spec**: baseline-measurement
**Epic**: aegf-infrastructure (Epic 0)
**Goal**: Capture pre-DSPy metrics across calibration quality, judge agreement, and compile duration so DSPy improvements are objectively measurable.

---

## User Stories

### US-1: Install scipy dependency
**Priority**: MUST
**Dependencies**: Spec: dependency-compatibility (adds numpy)

As a developer, I want scipy==1.17.1 declared in requirements.txt, pyproject.toml, and dependency_check.py so that the Spearman correlation baseline script can import scipy.stats.spearmanr.

**Acceptance Criteria**:
- [ ] scipy==1.17.1 appears in requirements.txt
- [ ] scipy==1.17.1 appears in pyproject.toml dependencies section
- [ ] scipy appears in infrastructure/dependency_check.py PACKAGE_IMPORT_MAP
- [ ] pip install scipy==1.17.1 works in the project environment (Python 3.14.3)

### US-2: Spearman correlation baseline
**Priority**: MUST
**Dependencies**: US-1 (scipy installed), reference dataset available

As an ML Engineer, I want to run `infrastructure/baselines/measure_spearman_baseline.py` on a reference dataset to capture pre-DSPy judge score agreement as a baseline Spearman correlation coefficient.

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/baselines/measure_spearman_baseline.py
- [ ] Script accepts --dataset path argument (reads judge_scores from fixture or JSON)
- [ ] Script accepts --output path argument (defaults to baseline_results/spearman_judge_baseline.json)
- [ ] Script computes weighted composite scores using SCORING_WEIGHTS from src/audit/schema.py: ha_modernity(0.30), reasoning_depth(0.25), functionality(0.25), completeness(0.12), style(0.08)
- [ ] Script computes scipy.stats.spearmanr between baseline and adapter composites
- [ ] Script handles n<3 edge case (returns structured error with reason="insufficient_samples")
- [ ] Script handles constant input edge case (returns rho=0.0, reason="constant_input")
- [ ] Script outputs JSON in baseline result schema to baseline_results/spearman_judge_baseline.json
- [ ] Output includes: type, timestamp (ISO8601), score (rho float), details with p_value, n, method (exact/asymptotic), pass_target (bool, true if rho > 0.8)
- [ ] Uses dependency_check.py rich CLI pattern (typed main, _die(), logging, raise SystemExit(main()))

### US-3: Calibration quality baseline
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want to run `infrastructure/baselines/run_calibration_baseline.py` to capture current calibration quality scores (coherence and LDI) as a baseline for future comparison.

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/baselines/run_calibration_baseline.py
- [ ] Script captures mean coherence from CalibrationResult.judge_scores["coherence"]
- [ ] Script sources LDI from curation pipeline outputs or SampleRecord.ldi (NOT from calibration results)
- [ ] Script accepts --dataset path argument and --output path argument
- [ ] Script outputs JSON in baseline result schema to baseline_results/calibration_baseline.json
- [ ] Output includes: type, timestamp (ISO8601), score (composite quality metric), details with mean_coherence, mean_ldi, ldi_pass_rate, grid_config, total_iterations
- [ ] Uses dependency_check.py rich CLI pattern (typed main, _die(), logging, raise SystemExit(main()))

### US-4: MIPROv2 compile baseline
**Priority**: SHOULD
**Dependencies**: None

As an ML Engineer, I want to run `infrastructure/baselines/measure_mipro_compile_baseline.py` to measure the current grid search duration, establishing a baseline for NFR-007 (MIPROv2 compile <= 3x baseline).

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/baselines/measure_mipro_compile_baseline.py
- [ ] Script measures grid search duration (wall-clock time from start to CalibrationReport)
- [ ] Script records grid configuration (CALIBRATION_GRID from src/audit/calibration_schema.py) alongside duration
- [ ] Script outputs JSON in baseline result schema to baseline_results/mipro_compile_baseline.json
- [ ] Output includes: type, timestamp (ISO8601), score (duration_seconds), details with grid_config, total_iterations, profiles_tested
- [ ] Uses dependency_check.py rich CLI pattern (typed main, _die(), logging, raise SystemExit(main()))

### US-5: Rollback verification
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want a rollback verification script that confirms git revert operations complete in under 1 minute (NFR-009).

**Acceptance Criteria**:
- [ ] Script exists at infrastructure/rollback_check.py
- [ ] Script creates a test commit, performs git revert HEAD~1
- [ ] Measures revert duration, verifies < 60 seconds (NFR-009)
- [ ] Verifies git status is clean after revert (no untracked or modified files)
- [ ] Returns exit code 0 if within target, 1 if exceeded
- [ ] Uses dependency_check.py rich CLI pattern (typed main, _die(), logging, raise SystemExit(main()))

### US-6: Project structure and conventions
**Priority**: MUST
**Dependencies**: None

As a developer, I want all baseline scripts to follow project conventions so they integrate seamlessly with existing tooling (check_headers, ruff, pyright, coverage).

**Acceptance Criteria**:
- [ ] All scripts include Apache-2.0 license header (3 tokens within first 4096 bytes: SPDX-License-Identifier:, Architect-Expert-Gap-Forge, Copyright)
- [ ] All scripts use `from __future__ import annotations` as first import
- [ ] infrastructure/baselines/ directory includes __init__.py
- [ ] Baseline scripts follow dependency_check.py rich CLI pattern (typed main, _die(), logging.basicConfig, raise SystemExit(main()))
- [ ] Output files use json.dump(data, f, indent=2)
- [ ] All scripts pass `ruff format`
- [ ] All scripts pass pyright type checking

---

## Functional Requirements

### FR-001: scipy dependency declaration
- [FR-001.1] scipy==1.17.1 MUST be added to requirements.txt
- [FR-001.2] scipy MUST be added to pyproject.toml dependencies section
- [FR-001.3] scipy MUST be added to infrastructure/dependency_check.py PACKAGE_IMPORT_MAP
- [FR-001.4] numpy must already be present in requirements.txt (verified by dependency-compatibility spec completion)

### FR-002: Spearman baseline script
- [FR-002.1] Script MUST exist at infrastructure/baselines/measure_spearman_baseline.py
- [FR-002.2] Script MUST accept --dataset path argument (reads judge_scores from fixture or JSON)
- [FR-002.3] Script MUST accept --output path argument (default: baseline_results/spearman_judge_baseline.json)
- [FR-002.4] Script MUST import and use SCORING_WEIGHTS from src/audit/schema.py
- [FR-002.5] Script MUST compute composite score: sum(score * weight for each dimension)
- [FR-002.6] Script MUST call scipy.stats.spearmanr(baseline_composites, adapter_composites)
- [FR-002.7] Script MUST handle n<3 edge case (return structured error with reason="insufficient_samples", p_value=nan, rho=nan)
- [FR-002.8] Script MUST handle constant input edge case (catch scipy.stats.ConstantInputError or detect via len(set())<=1, return rho=0.0, p_value=1.0, reason="constant_input")
- [FR-002.9] Script MUST use method="exact" for n<10, method="asymptotic" for n>=10
- [FR-002.10] Script MUST output JSON with type="spearman_baseline", timestamp (ISO8601), score (rho float), details (p_value, n, method, pass_target)
- [FR-002.11] pass_target MUST be True when rho > 0.8 (NFR-002)

### FR-003: Calibration baseline script
- [FR-003.1] Script MUST exist at infrastructure/baselines/run_calibration_baseline.py
- [FR-003.2] Script MUST capture mean coherence from CalibrationResult.judge_scores["coherence"]
- [FR-003.3] Script MUST source LDI from curation pipeline outputs or SampleRecord.ldi (NOT from calibration results)
- [FR-003.4] Script MUST accept --dataset path argument and --output path argument
- [FR-003.5] Script MUST output JSON with type="calibration_baseline", timestamp (ISO8601), score (float composite), details (mean_coherence, mean_ldi, ldi_pass_rate, grid_config, total_iterations)
- [FR-003.6] grid_config MUST include CALIBRATION_GRID from src/audit/calibration_schema.py (temperature, top_k, min_p, repetition_penalty, presence_penalty arrays)

### FR-004: MIPROv2 compile baseline script
- [FR-004.1] Script MUST exist at infrastructure/baselines/measure_mipro_compile_baseline.py
- [FR-004.2] Script MUST measure wall-clock grid search duration using time.perf_counter()
- [FR-004.3] Script MUST record grid configuration alongside duration
- [FR-004.4] Script MUST output JSON with type="mipro_compile", timestamp (ISO8601), score (duration_seconds), details (grid_config, total_iterations, profiles_tested)
- [FR-004.5] Script MUST report profiles_tested = profiles × prompts (e.g., 4500 × 6 = 27000)

### FR-005: Rollback verification script
- [FR-005.1] Script MUST exist at infrastructure/rollback_check.py
- [FR-005.2] Script MUST create a test commit (git add + git commit)
- [FR-005.3] Script MUST measure git revert HEAD~1 duration using time.perf_counter()
- [FR-005.4] Script MUST verify < 60 second threshold (NFR-009)
- [FR-005.5] Script MUST verify git status is clean after revert (no modified or untracked files)
- [FR-005.6] Script MUST return exit code 0 if within target, 1 if exceeded

### FR-006: Project structure
- [FR-006.1] infrastructure/baselines/ directory MUST be created with __init__.py
- [FR-006.2] baseline_results/ directory MUST be created at project root
- [FR-006.3] baseline_results/ MUST be added to .gitignore (runtime data, not source control)
- [FR-006.4] All scripts MUST follow dependency_check.py CLI pattern (typed main, _die(), logging, raise SystemExit(main()))
- [FR-006.5] All scripts MUST pass ruff format
- [FR-006.6] All scripts MUST pass pyright type checking
- [FR-006.7] All scripts MUST include Apache-2.0 license header (3 tokens within first 4096 bytes)

---

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-002 | Spearman correlation target | rho > threshold | > 0.8 with existing judge.py scores |
| NFR-007 | MIPROv2 compile duration | compile_time <= 3x | baseline measured by this spec |
| NFR-009 | Rollback time | git revert duration | < 60 seconds |
| NFR-010 | Code quality | ruff format + pyright | All baseline scripts pass |

### NFR-001: Performance (implicit)
- Spearman baseline script: < 5 minutes (reads pre-computed scores, no live API)
- Calibration baseline script: depends on data source; if reading existing curation outputs, < 1 minute; if running curation pipeline, up to 30 minutes
- MIPROv2 compile baseline: actual grid duration (27,000 iterations) — this IS the measurement, not a constraint

---

## Glossary

| Term | Definition |
|------|-----------|
| **SCORING_WEIGHTS** | Stage 5 judge dimension weights (src/audit/schema.py:39-45): ha_modernity(0.30), reasoning_depth(0.25), functionality(0.25), completeness(0.12), style(0.08) |
| **CALIBRATION_SCORING_WEIGHTS** | Stage 6 judge dimension weights (src/audit/schema.py:49-55): parameter_effectiveness(0.30), task_completion(0.20), parameter_alignment(0.25), coherence(0.15), style(0.10) |
| **LDI** | Length Density Index — curation/factory pipeline quality filter, NOT a calibration scoring dimension. Factory LDI: K=1200, character-level. Curation LDI: K=800, token-level |
| **NFR-002** | Spearman correlation > 0.8 target for DSPy improvement assessment |
| **NFR-007** | MIPROv2 compile duration <= 3x baseline measured by this spec |
| **NFR-009** | Rollback via git revert must complete in < 60 seconds |
| **Calibration grid** | 4,500 profiles x 6 prompts = 27,000 API calls (src/audit/calibration_schema.py:66-72) |
| **CalibrationReport** | Frozen dataclass (src/audit/calibration_schema.py:209-251) with timestamp, total_iterations, best_profile, statistics |
| **NormalizedJudgeResponse** | TypedDict with baseline, adapter dict[str, float] and reasoning str (src/audit/schema.py:81) |

---

## Out of Scope

- DSPy implementation or optimization (covered by Epic 1: aegf-dspy-integration)
- Live LLM inference for Spearman baseline (reads pre-computed scores from fixtures/files)
- Running the curation pipeline (baseline reads existing curation outputs, does not trigger curation)
- Implementing grid search (baseline MEASURES existing calibration, does not implement grid search)
- Test suite (tests added in Epic 1)
- CI/CD integration for baseline comparisons
- Historical baseline trend analysis or dashboards

---

## Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| Spec: dependency-compatibility | Completed (but MISSED scipy) | Adds scipy==1.17.1 to requirements.txt as part of this spec |
| Spec: prompt-externalization | Completed | Provides .example.yaml reference patterns |
| src/audit/schema.py | Available | SCORING_WEIGHTS, CALIBRATION_SCORING_WEIGHTS, NormalizedJudgeResponse |
| src/audit/scorecard.py | Available | _composite function pattern |
| src/audit/calibration_schema.py | Available | CalibrationReport, CALIBRATION_GRID |
| src/factory/ldi_validator.py | Available | Factory LDI pattern |
| src/curation/quality_filter.py | Available | Curation LDI pattern |
| tests/fixtures/calibration_examples.json | Available | 4 entries with Stage 5 judge_scores |
| tests/fixtures/judge_scoring_response.json | Available | Full judge output |
| tests/fixtures/inference_results.json | Available | baseline + adapter responses |

---

## Success Criteria

- All 4 baseline scripts exist and run without errors
- baseline_results/ contains valid JSON output from each script
- scipy==1.17.1 is declared in all required locations
- All scripts pass ruff format and pyright type checking
- NFR-009 (rollback < 60s) is verified by rollback_check.py
- Baseline metrics are captured before any DSPy changes

---

## Verification Contract

**Project type**: `api-only`

This spec creates infrastructure/baselines/ scripts that read data from existing fixtures and API outputs. There is no browser UI. The scripts call scipy (local computation) and potentially the calibration infrastructure (local imports). No HTTP server is required.

**Entry points**:
- CLI: `python infrastructure/baselines/measure_spearman_baseline.py --dataset <path> --output <path>`
- CLI: `python infrastructure/baselines/run_calibration_baseline.py --dataset <path> --output <path>`
- CLI: `python infrastructure/baselines/measure_mipro_compile_baseline.py --dataset <path> --output <path>`
- CLI: `python infrastructure/rollback_check.py`
- File reads: tests/fixtures/calibration_examples.json, tests/fixtures/judge_scoring_response.json, tests/fixtures/inference_results.json
- Import: src/audit/schema.py (SCORING_WEIGHTS), src/audit/calibration_schema.py (CALIBRATION_GRID)

**Observable signals**:
- PASS: Script exits with code 0, output JSON file exists, JSON has type/timestamp/score/details fields
- FAIL: Script exits with code 1, stderr contains error, output file missing or malformed JSON
- Spearman PASS: spearman_judge_baseline.json has score > 0.8 (if dataset has > 3 entries)
- Calibration PASS: calibration_baseline.json has mean_coherence and mean_ldi > 0
- Rollback PASS: revert completes in < 60s, git status shows clean working tree

**Hard invariants**:
- Auth/session: not applicable (local scripts)
- Data integrity: baseline output JSON must not corrupt existing fixtures
- Import safety: scripts must not modify src/audit/schema.py or src/audit/calibration_schema.py
- Adjacent flows: scipy installation must not break existing imports in src/ or scripts/

**Seed data**:
- tests/fixtures/calibration_examples.json: 4 entries with baseline/adapter judge_scores (required for Spearman baseline)
- tests/fixtures/judge_scoring_response.json: full judge output (reference)
- src/audit/schema.py: SCORING_WEIGHTS constant (required import)
- src/audit/calibration_schema.py: CALIBRATION_GRID constant (required import for calibration/mipro baselines)

**Dependency map**:
- `dependency-compatibility` spec: shares requirements.txt and pyproject.toml for scipy declaration
- `src/audit/schema.py`: read-only import (SCORING_WEIGHTS)
- `src/audit/calibration_schema.py`: read-only import (CALIBRATION_GRID)
- `scripts/benchmark/compare_baseline.py`: pattern reference only (not imported)
- `infrastructure/dependency_check.py`: pattern reference only (not imported)

**Escalate if**:
- scipy==1.17.1 fails to install on Python 3.14.3 in the project environment
- calibration_examples.json fixture is missing or has wrong structure (no baseline/adapter keys)
- dependency-compatibility spec has not added numpy to requirements.txt (blocks scipy installation on Python 3.14 due to numpy dependency)
- Grid search configuration (CALIBRATION_GRID) has changed since research — verify against live code

---

## Unresolved Questions

- LDI data source: calibration baseline script must read LDI from existing curation outputs (SampleRecord.ldi field or curation pipeline JSON files). The exact file path is project-specific and should be configurable via --ldi-source argument. If no curation outputs exist, the script should produce a graceful warning with mean_ldi=null.
- Grid size for MIPRO baseline: the script MEASURES existing grid duration. If the grid has not been run, the script should read CALIBRATION_GRID from src/audit/calibration_schema.py and compute total_iterations=27000 without actually running the grid (live grid execution would require API keys and significant time).
- scipy as hard vs optional dependency: research confirmed scipy==1.17.1 works on all Python 3.11-3.14 with identical wheel coverage. Adding as a hard dependency (not optional) since it is required for the primary Spearman use case.

## Next Steps

1. Confirm scipy is added to dependency-compatibility spec or directly in this spec (dependency-compatibility is marked completed but research shows scipy was missed)
2. Create infrastructure/baselines/ directory with __init__.py
3. Create baseline_results/ directory at project root
4. Implement measure_spearman_baseline.py
5. Implement run_calibration_baseline.py
6. Implement measure_mipro_compile_baseline.py
7. Implement rollback_check.py
8. Run all scripts against test fixtures and verify output schema
9. Run ruff format + pyright on all new scripts
10. Commit and push

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
