# Spec: langgraph-conditional-edges

**Epic:** specs/_epics/aegf-langgraph-inference/epic.md
**Size:** S (~1-2 days, ~100-150 LOC)
**Status:** pending (blocked on: langgraph-graph)

## BMAD Source

- **Story:** 3.2b — LangGraph Conditional Edges (SPLIT from 3.2)
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:660`](../../_bmad-output/planning-artifacts/epics.md#story-32b-langgraph-conditional-edges-split-from-32)

## Goal

As a Platform Operator, I want conditional edges in the LangGraph state machine, so that migration decisions are based on audit scores.

## Acceptance Criteria

**Given** the graph skeleton (Story 3.2a),
**When** I add conditional edges,
**Then** conditional edge logic: `if audit_score >= threshold → export, else → recode`
**And** the edge function is in `src/inference/conditional_edges.py`
**And** threshold is configurable via `configs/inference/graph_thresholds.yaml`

## Interface Contracts

### Writes
- `src/inference/conditional_edges.py`
- `configs/inference/graph_thresholds.yaml`

### Reads
- `src/inference/migration_state.py` (MigrationState for audit_score field)

## Dependencies

- **Spec: langgraph-graph** (graph skeleton must exist)

## Implementation Notes

- Conditional edge is a routing function: `def route_after_auditor(state: MigrationState) -> str`
- Returns `"export"` if audit_score >= threshold, `"recode"` otherwise
- Threshold value from YAML config (default TBD)
