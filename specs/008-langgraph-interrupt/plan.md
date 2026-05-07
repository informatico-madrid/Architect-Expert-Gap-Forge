# Spec: langgraph-interrupt

**Epic:** specs/_epics/aegf-langgraph-inference/epic.md
**Size:** S (~1 day, ~50-100 LOC)
**Status:** pending (blocked on: langgraph-conditional-edges)

## BMAD Source

- **Story:** 3.2c — LangGraph Interrupt Mechanism (SPLIT from 3.2)
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:682`](../../_bmad-output/planning-artifacts/epics.md#story-32c-langgraph-interrupt-mechanism-split-from-32)

## Goal

As a Platform Operator, I want `interrupt()` triggered after max_rounds without consensus, so that human intervention is requested when the graph cannot converge.

## Acceptance Criteria

**Given** the graph with conditional edges (Story 3.2b),
**When** the graph executes max_rounds without achieving consensus,
**Then** `interrupt()` is triggered
**And** state is preserved at the point of interruption
**And** human notification mechanism is activated (Story 3.3)

## Interface Contracts

### Writes
- `src/inference/graph.py` (interrupt logic integrated)

### Reads
- `src/inference/migration_state.py` (MigrationState with consensus field)

## Dependencies

- **Spec: langgraph-conditional-edges** (conditional edges must exist)

## Implementation Notes

- Integrated directly into `src/inference/graph.py`
- Uses LangGraph's built-in `interrupt()` API
- State is automatically preserved at interrupt point
