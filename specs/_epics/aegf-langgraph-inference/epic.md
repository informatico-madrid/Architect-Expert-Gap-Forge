---
name: aegf-langgraph-inference
goal: Implement LangGraph-based migration state machine with 3-agent architecture (Winston the Architect, Amelia the Coder, Murat the Auditor) plus an Ingest node for data loading, conditional edges, interrupt mechanism, and checkpointing for fault recovery.
version: 1.0
date: 2026-04-29
status: planning
storyCount: 5
specs:
  - 005-migration-state
  - 006-langgraph-graph
  - 007-langgraph-conditional-edges
  - 008-langgraph-interrupt
  - 009-langgraph-checkpointing
---

# Epic: aegf-langgraph-inference

## Epic Goal

Build the LangGraph Layer 2 state machine that orchestrates migration planning and execution through three specialized agents: Winston (Architect — proposes migration plans), Amelia (Coder — implements migrations), and Murat (Auditor — scores quality). Includes conditional routing, human interrupt on stalemate, and checkpointing for crash recovery.

## BMAD Sources

This epic is decomposed from **BMAD Epic 3: Layer 2 LangGraph Inference** (`_bmad-output/planning-artifacts/epics.md` v4.0).
All 5 stories (including Story 3.2 split into 3.2a/3.2b/3.2c), acceptance criteria, and dependencies are sourced directly from the BMAD epics document.

| BMAD Document | Role in This Epic |
|---------------|-------------------|
| [epics.md](../../../_bmad-output/planning-artifacts/epics.md) | **Primary** — story definitions (3.1, 3.2a-c, 3.3), AC, dependencies |
| [aegf-3-layer-prd.md](../../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) | PRD requirements for state machine orchestration |
| [architecture.md](../../../_bmad-output/planning-artifacts/architecture.md) | 3-agent node structure, state machine context |

### Story References (epics.md line numbers)

| Story | epics.md Reference | Spec Directory |
|-------|-------------------|----------------|
| 3.1 MigrationState TypedDict | epics.md:603 | `specs/005-migration-state/` |
| 3.2a Graph Skeleton (SPLIT) | epics.md:633 | `specs/006-langgraph-graph/` |
| 3.2b Conditional Edges (SPLIT) | epics.md:660 | `specs/007-langgraph-conditional-edges/` |
| 3.2c Interrupt (SPLIT) | epics.md:682 | `specs/008-langgraph-interrupt/` |
| 3.3 Checkpointing (SPLIT) | epics.md:704 | `specs/009-langgraph-checkpointing/` |

## Scope

### IN Scope

- MigrationState TypedDict with all required fields (legacy_code, target_architecture, migration_plan, proposed_code, audit_score, audit_feedback, consensus, debate_rounds, max_rounds)
- LangGraph state machine skeleton with 4 nodes (3 agents + Ingest data loader): Architect/Winston, Coder/Amelia, Auditor/Murat, and Ingest
- Conditional edges: audit_score >= threshold → export, else → recode
- Configurable threshold via `configs/inference/graph_thresholds.yaml`
- Interrupt mechanism: `interrupt()` triggered when max_rounds reached without consensus
- Human notification: email (SMTP), webhook, or log fallback
- PostgresSaver checkpointing for crash recovery
- Human override: approve, reject, or modify migration plan

### OUT of Scope

- Model fine-tuning (Epic 1/2 territory)
- Production deployment infrastructure
- Multi-tenant or distributed deployment
- Real-time streaming updates

## Dependencies

**Prerequisites:** Epic X gate must pass (all Epic 0/1/2 criteria met).

| Spec | Depends On | Status |
|------|-----------|--------|
| 005-migration-state | Epic X gate | plan.md created |
| 006-langgraph-graph | 005-migration-state | plan.md created |
| 007-langgraph-conditional-edges | 006-langgraph-graph | plan.md created |
| 008-langgraph-interrupt | 007-langgraph-conditional-edges | plan.md created |
| 009-langgraph-checkpointing | 008-langgraph-interrupt | plan.md created |

**Execution Order:** Strictly sequential (3.1 → 3.2a → 3.2b → 3.2c → 3.3). Each story builds on the previous one's state machine components.

## Interface Contracts

### MigrationState (TypedDict)
- **File:** `src/inference/migration_state.py`
- **Fields:** legacy_code (str), target_architecture (str), migration_plan (str), proposed_code (str), audit_score (float), audit_feedback (str), consensus (bool), debate_rounds (int), max_rounds (int)

### Graph Nodes
- **File:** `src/inference/graph.py`
- **Ingest:** loads legacy code + target architecture into state
- **Architect (Winston):** proposes migration plan
- **Coder (Amelia):** implements migration using model
- **Auditor (Murat):** scores migration quality

### Conditional Edges
- **File:** `src/inference/conditional_edges.py`
- **Function:** `def route_after_auditor(state: MigrationState) -> str`
- **Config:** `configs/inference/graph_thresholds.yaml`

### Notification
- **Config:** `configs/inference/notification.yaml`
- **Fallback:** `logs/interrupt_requests.log`

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Postgres required for checkpointing (infrastructure dependency) | HIGH | Document in plan.md; provide in-memory fallback for POC |
| LangGraph API stability (pre-1.0) | MEDIUM | Pin exact version; monitor release notes |
| 3-agent orchestration complexity | MEDIUM | POC first (Phase 1), then refactor (Phase 2) |
| Human interrupt workflow undefined | LOW | Default: email → webhook → log; make configurable |
| Circular dependency with gate | LOW | Gate precedes Epic 3 by design (no cycle) |
