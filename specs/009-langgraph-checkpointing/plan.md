# Spec: langgraph-checkpointing

**Epic:** specs/_epics/aegf-langgraph-inference/epic.md
**Size:** M (~2-3 days)
**Status:** pending (blocked on: langgraph-interrupt)

## BMAD Source

- **Story:** 3.3 — Checkpointing and Fault Recovery
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:704`](../../_bmad-output/planning-artifacts/epics.md#story-33-checkpointing-and-fault-recovery)

## Goal

As a Platform Operator, I want checkpointing and fault recovery in LangGraph, so that long migrations can resume after crashes.

## Acceptance Criteria

1. **Checkpoint on crash:** Given a migration graph executing, when a crash occurs at any node, `PostgresSaver` checkpoint preserves MigrationState.
2. **Resume from checkpoint:** When the graph restarts, it resumes from the last checkpointed state. No work is lost (up to last successful node transition).
3. **Human notification on max_rounds:** When `max_rounds` reached without consensus, `interrupt()` is triggered and:
   - Email to operator via SMTP config, OR
   - Webhook to monitoring system (configurable)
   - Fallback: write to `logs/interrupt_requests.log`
4. **Human override:** Human can approve, reject, or modify the migration plan.

## Interface Contracts

### Writes
- Checkpoint state via `PostgresSaver`
- Notification via configured mechanism (SMTP/webhook/log)
- `configs/inference/notification.yaml` (new)
- `logs/interrupt_requests.log` (runtime)

### Reads
- `src/inference/migration_state.py` (MigrationState)
- `src/inference/graph.py` (graph with interrupt mechanism)

## Dependencies

- **Spec: langgraph-interrupt** (interrupt mechanism must exist)
- **PostgreSQL** for checkpoint persistence (infrastructure dependency)

## Implementation Notes

- PostgresSaver is the LangGraph built-in persistence mechanism
- Notification config at `configs/inference/notification.yaml`
- Default: email if SMTP configured, else webhook, else log
- Human approval loop: operator receives notification → reviews migration → approves/rejects/modifies
