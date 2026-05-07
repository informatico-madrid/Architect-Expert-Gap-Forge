---
name: aegf-integration-gate
goal: Validate that Epic 0, Epic 1, and Epic 2 stories meet acceptance criteria before proceeding to Epic 3 (LangGraph Layer 2). Acts as an inter-epic quality gate checkpoint.
version: 1.0
date: 2026-04-29
status: planning
storyCount: 0
specs:
  - 004-eic-integration-gate
---

# Epic: aegf-integration-gate (Epic 2.5)

## Epic Goal

Validate ALL Epic 0, Epic 1, and Epic 2 stories meet acceptance criteria before proceeding to Epic 3 (LangGraph Layer 2). This is NOT a story — it is a GATE CHECKPOINT.

## Origin and Rationale

This was originally Story 2.4 inside Epic 2 (BMAD v3.x). In v4.0, Winston moved it to an independent inter-epic gate to resolve a circular dependency:

- **Before:** Epic 2 depended on Epic 1 being complete (gate inside Epic 2 checked Epic 1), but the gate was inside Epic 2. This created a cycle: Epic 2 → Gate → Epic 1 → (indirect dependency) → Epic 2.
- **After:** Gate is an independent Epic 2.5 that sits between Epic 2 and Epic 3. Epic 0 → Epic 1 → Epic 2 → Gate → Epic 3.

| Gate Criterion | Threshold | Measurement |
|---------------|-----------|-------------|
| Spearman Correlation | > 0.8 | `scripts/measure_recall.py --spearman` |
| Judge Score | >= 0.75 | Stage 5 audit output |
| Test Coverage | >= 90% | `pytest --cov=src --cov-report=json` |
| Calibration Grid Reduction | >= 50% | Stage 6 output vs baseline |
| Pipeline Throughput | No regression | Stage 1-6 timing vs pre-DSPy |
| Autonomous Cycles | >= 3 | `.ralph/` logs |
| Rollback Time | < 1 min | `time git revert HEAD~1` |
| Anchor Dataset Verified | 100-200 samples | `datasets/anchors/v1/anchor_manifest.json` |
| Dependency Compat Verified | No conflicts | `infrastructure/dependency_check.py` |

## BMAD Sources

| BMAD Document | Role in This Epic |
|---------------|-------------------|
| [epics.md](../../../_bmad-output/planning-artifacts/epics.md) | Gate definition (Story X / 2.5, lines 566-598) |
| [aegf-3-layer-prd.md](../../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) | NFR-002, NFR-007, NFR-009 thresholds |

### Gate Execution

```bash
# Run gate validation
python -m infrastructure.gate_validation --epics 0,1,2

# If all criteria pass, Epic 3 is unblocked
# If any criterion fails, return to Epic 0/1/2 stories for fix
```

## Smart Ralph Mapping

This epic maps to a single spec:

| BMAD Story | Smart Ralph Spec | Status |
|-----------|-----------------|--------|
| Epic X (Gate) | `specs/004-eic-integration-gate/plan.md` | plan.md created |

**Note:** The integration gate is a validation step, not a feature implementation. The `plan.md` documents gate criteria, dependencies, and execution procedure. Actual gate validation runs as part of the overall project workflow, not as a standalone spec implementation.

## Scope

### IN Scope

- Gate criteria definition and documentation
- Gate execution procedure specification
- Dependency tracking (Epic 0, 1, 2 completion status)
- Pass/fail reporting for each gate criterion

### OUT of Scope

- Fixing failing gate criteria (these trace back to Epic 0/1/2)
- Epic 3 implementation (unblocked by gate, but gate doesn't implement it)
- New feature development

## Dependencies

**Prerequisites:** All stories in Epic 0, Epic 1, and Epic 2 must be complete.

| Dependency | Epic | Specs |
|-----------|------|-------|
| Baseline + Prompts + Anchors + Dependencies | Epic 0 | 4 specs |
| DSPy Signatures | Epic 1 | 1 spec (dspy-integration) |
| Dataset + Preservation + Multi-lang | Epic 2 | 3 specs |
