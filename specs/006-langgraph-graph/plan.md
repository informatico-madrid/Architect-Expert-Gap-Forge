# Spec: langgraph-graph

**Epic:** specs/_epics/aegf-langgraph-inference/epic.md
**Size:** M (~2-3 days, ~200-300 LOC)
**Status:** pending (blocked on: migration-state)

## BMAD Source

- **Story:** 3.2a — LangGraph Graph Skeleton (SPLIT from 3.2)
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:633`](../../_bmad-output/planning-artifacts/epics.md#story-32a-langgraph-graph-skeleton-split-from-32)
- **Architecture:** [architecture.md](../../_bmad-output/planning-artifacts/architecture.md) — 3-agent node structure

## Goal

As a Platform Operator, I want the LangGraph state machine skeleton with 3 agent nodes, so that the migration graph has a working structure.

## Acceptance Criteria

**Given** MigrationState TypedDict (Story 3.1),
**When** I implement the migration graph skeleton,
**Then** it includes:
- Ingest node: loads legacy code + target architecture into state
- Architect node (Winston): proposes migration plan
- Coder node (Amelia): implements migration using fine-tuned model
- Auditor node (Murat): scores migration quality
**And** graph compiles without errors: `python -c "from src.inference.graph import migration_graph"`
**And** each node accepts MigrationState and returns updated MigrationState

## Interface Contracts

### Writes
- `src/inference/graph.py`

### Reads
- `src/inference/migration_state.py` (MigrationState)

## Dependencies

- **Spec: migration-state** (MigrationState TypedDict must exist)

## Implementation Notes

- Skeleton only — no conditional edges yet (Story 3.2b)
- No interrupt mechanism yet (Story 3.2c)
- Each node function takes MigrationState, returns MigrationState
- Graph compiles: `LangGraph(migration_graph)` without errors
