# Spec: baseline-measurement

**Epic:** specs/_epics/aegf-infrastructure/epic.md
**Size:** S (1-2 days)
**Status:** pending (blocked on: dependency-compatibility)

## BMAD Source

- **Story:** 0.1 — Baseline Measurement Infrastructure
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:206`](../../_bmad-output/planning-artifacts/epics.md#story-01-baseline-measurement-infrastructure)
- **PRD:** [aegf-3-layer-prd.md](../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) — NFR-002 (Spearman >0.8), NFR-007 (MIPROv2 compile), NFR-009 (rollback <1 min)
- **Sprint Status:** [sprint-status.yaml](../../_bmad-output/implementation-artifacts/sprint-status.yaml) — story 0.1, status: backlog
- **Product Brief:** [aegf-autonomous-forge-product-brief.md](../../_bmad-output/planning-artifacts/aegf-autonomous-forge-product-brief.md) — NFR-009 rollback time evidence

## Goal

As an ML Engineer, I want baseline metrics captured before implementing DSPy features, so that I can objectively measure whether DSPy improves or degrades performance.

## Acceptance Criteria

1. **Spearman correlation baseline:** Running `infrastructure/baselines/measure_spearman_baseline.py` on a reference dataset produces a Spearman correlation score stored in `baseline_results/spearman_judge_baseline.json`. Script reuses `scripts/benchmark/compare_baseline.py` patterns for result storage.

2. **Calibration quality baseline:** Running `infrastructure/baselines/run_calibration_baseline.py` records current calibration quality scores (LDI, coherence) in `baseline_results/calibration_baseline.json`.

3. **Rollback verification:** `git revert HEAD~1` on a test commit reverts in < 1 minute with no corruption. `git status` shows clean working tree after revert.

4. **MIPROv2 compile baseline:** Running `infrastructure/baselines/measure_mipro_compile_baseline.py` measures current grid search duration and stores it (for NFR-007: MIPROv2 compile <= 3x baseline).

## Interface Contracts

### Writes
- `infrastructure/baselines/measure_spearman_baseline.py`
- `infrastructure/baselines/run_calibration_baseline.py`
- `infrastructure/baselines/measure_mipro_compile_baseline.py`
- `infrastructure/rollback_check.py`

### Writes (runtime data)
- `baseline_results/spearman_judge_baseline.json`
- `baseline_results/calibration_baseline.json`
- `baseline_results/mipro_compile_baseline.json`

### Reads
- `scripts/benchmark/compare_baseline.py` (pattern reuse)
- Existing `src/audit/judge.py` output
- Existing `src/audit/calibration.py` output

### Baseline Result Schema
```json
{
  "type": "spearman_baseline|calibration_baseline|mipro_compile",
  "timestamp": "ISO8601",
  "score": <float>,
  "details": {}
}
```

## Dependencies

- **Spec: dependency-compatibility** (must complete first) -- scipy and numpy must be in requirements.txt before baseline scripts can run.

## Implementation Notes

- `infrastructure/` and `infrastructure/baselines/` directories do NOT exist -- must be created
- `scripts/benchmark/baselines/` subdirectory exists but is EMPTY
- `scripts/benchmark/compare_baseline.py` (224 lines) provides reusable pattern for result storage
- Spearman correlation must use `scipy.stats.spearmanr`
- `numpy` is imported by `measure_performance.py` but NOT in requirements.txt (pre-existing bug fixed by Spec: dependency-compatibility)
