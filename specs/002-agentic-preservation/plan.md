# Spec: agentic-preservation

**Epic:** specs/_epics/aegf-dataset-training/epic.md
**Size:** XL (requires model training — may be AC of Epic 2 complete)
**Status:** pending (blocked on: dataset-mixing)

## BMAD Source

- **Story:** 2.2 — Validate Agentic Capability Preservation
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:524`](../../_bmad-output/planning-artifacts/epics.md#story-22-validate-agentic-capability-preservation)
- **PRD:** [aegf-3-layer-prd.md](../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) — NFR-002 (Spearman >0.8), NFR-007 (MIPROv2 compile)
- **Party Mode Note (Winston):** "This story has high individual cost (requires training a model). Consider making it an acceptance criterion of Epic 2 complete rather than a standalone story."

## Goal

As an ML Engineer, I want to verify that dataset mixing preserves tool usage capability, so that the model doesn't degrade on agentic tasks.

## Acceptance Criteria

1. **Tool usage accuracy:** After training on the mixed dataset, the model achieves >= 80% tool usage accuracy measured on BFCL benchmark or ToolWatch.
2. **Migration quality:** The mixed-dataset trained model's migration quality >= baseline from pure AEGF dataset.
3. **Both metrics validated before final training run.**

## Agentic Benchmark Definition

- **Primary:** BFCL (Berkeley Function Calling Leaderboard) or ToolWatch
- **Fallback:** Custom benchmark using agentic test cases in `tests/fixtures/agentic_benchmark/`

## Interface Contracts

### Reads
- Mixed dataset from Story 2.1
- BFCL benchmark data or ToolWatch evaluation suite

### Writes
- Benchmark results: `evaluation/agentic_preservation.json`
- Migration quality comparison: `evaluation/migration_quality.json`

## Dependencies

- **Spec: dataset-mixing** (mixed dataset must exist)
- **Hugging Face `datasets`** + BFCL/ToolWatch evaluation dependencies

## Implementation Notes

- Requires actual model training (high compute cost)
- Winston recommended treating this as Epic 2 completion criterion instead of standalone story
- Benchmark infrastructure may need to be built from scratch
