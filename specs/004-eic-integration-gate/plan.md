# Spec: eic-integration-gate

**Epic:** specs/_epics/aegf-infrastructure/epic.md (moved from Epic 2.4)
**Size:** XS (< 1 day — validation script)
**Status:** pending (blocked on: Epic 2 complete)

## BMAD Source

- **Component:** Epic X — Layer 1 Integration Gate
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:566`](../../_bmad-output/planning-artifacts/epics.md#epic-x-layer-1-integration-gate-inter-epic-gate)
- **Change:** v4.0-C5: "Epic 2.4 moved to independent inter-epic gate (Winston)"

## Goal

Objective validation checkpoint before proceeding to Epic 3 (LangGraph Layer 2). Validates ALL Epic 0, Epic 1, and Epic 2 stories meet acceptance criteria.

**Why this exists:** Story 2.4 was originally inside Epic 2, creating a circular dependency: Epic 2 depends on Epic 1 being complete (gate), but the gate was inside Epic 2. Moving to an independent inter-epic gate eliminates this cycle.

**This is NOT a story.** This is a gate checkpoint that validates 9 criteria before unblocking Epic 3.

## Gate Criteria (ALL must pass)

| # | Criterion | Threshold | Measurement |
|---|---|---|---|
| 1 | Spearman Correlation | > 0.8 | `scripts/measure_recall.py --spearman` |
| 2 | Judge Score | >= 0.75 | Stage 5 audit output |
| 3 | Test Coverage | >= 90% | `pytest --cov=src --cov-report=json` |
| 4 | Calibration Grid Reduction | >= 50% | Stage 6 output vs baseline |
| 5 | Pipeline Throughput | No regression | Stage 1-6 timing vs pre-DSPy |
| 6 | Autonomous Cycles | >= 3 | `.ralph/` logs |
| 7 | Rollback Time | < 1 min | `time git revert HEAD~1` |
| 8 | Anchor Dataset Verified | 100-200 samples | `datasets/anchors/v1/anchor_manifest.json` |
| 9 | Dependency Compat Verified | No conflicts | `infrastructure/dependency_check.py` |

## Execution

```bash
# Run gate validation
python -m infrastructure.gate_validation --epics 0,1,2

# If all criteria pass → Epic 3 is unblocked
# If any criterion fails → return to Epic 0/1/2 stories for fix
```

## Gate Dependencies

All stories in Epic 0, Epic 1, and Epic 2 must be marked **done** before this gate runs.

## Implementation Notes

- Gate validation script at `infrastructure/gate_validation.py` (NEW)
- Each criterion has its own sub-command: `python -m infrastructure.gate_validation spearman`, etc.
- Gate result: PASS (all 9 pass) or FAIL (list which failed)
- This spec produces NO feature code — only a validation harness
