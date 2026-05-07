# Spec: migration-state

**Epic:** specs/_epics/aegf-langgraph-inference/epic.md
**Size:** XS (< 1 day)
**Status:** pending (blocked on: Epic X gate)

## BMAD Source

- **Story:** 3.1 — MigrationState TypedDict Definition
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:603`](../../_bmad-output/planning-artifacts/epics.md#story-31-migrationstate-typeddict-definition)
- **Architecture:** [architecture.md](../../_bmad-output/planning-artifacts/architecture.md) — LangGraph state machine context

## Goal

As a Platform Operator, I want MigrationState TypedDict defined with all required fields, so that the LangGraph state machine has a typed contract.

## Acceptance Criteria

**Given** the requirement for multi-agent migration,
**When** I define MigrationState TypedDict,
**Then** it includes these fields:
- `legacy_code: str`
- `target_architecture: str`
- `migration_plan: str`
- `proposed_code: str`
- `audit_score: float`
- `audit_feedback: str`
- `consensus: bool`
- `debate_rounds: int`
- `max_rounds: int`

## Interface Contracts

### Writes
- `src/inference/migration_state.py`

### Reads
- Architecture doc: [architecture.md](../../_bmad-output/planning-artifacts/architecture.md)

## Dependencies

- **Epic X gate must pass** (gate dependency from epics.md)

## Implementation Notes

- Use TypedDict with `Required[]` for mandatory fields
- Add runtime validation via Pydantic or typed validation
- This is a data structure definition only — no graph logic yet
