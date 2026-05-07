# Epic 0: Infrastructure Setup

**BMAD Epic 0** from `_bmad-output/planning-artifacts/epics.md` (v4.0).

**User Outcome:** ML Engineer puede validar todo objectivamente con metrics y baselines antes de implementar features. Tiene datos ancla para DSPy MIPROv2 y dependencias compatibles.

**Stories:** 4 (0.1 Baseline, 0.2 Prompt Externalization, 0.3 Anchor Dataset, 0.4 Dependency Compat)
**Specs:** 4 (baseline-measurement, prompt-externalization, anchor-dataset, dependency-compatibility)

---

## BMAD Documentation References

### Planning Artifacts (source of truth for stories)
| Document | Relevance | Location |
|----------|-----------|----------|
| [epics.md](../../../_bmad-output/planning-artifacts/epics.md) | **Primary** — defines all 4 stories with acceptance criteria | v4.0, Party Mode validated |
| [aegf-3-layer-prd.md](../../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) | **Primary** — architecture, FRs, NFRs, DSPy integration details | Draft v3 unified |
| [aegf-autonomous-forge-product-brief.md](../../../_bmad-output/planning-artifacts/aegf-autonomous-forge-product-brief.md) | **Primary** — problem statement, product vision, hard-coding evidence | Draft v2 |
| [architecture.md](../../../_bmad-output/planning-artifacts/architecture.md) | **Primary** — architectural decisions, 2-layer structure | |
| [PRD-EXPLICADO-PARA-HUMANOS-TONTOS.md](../../../_bmad-output/planning-artifacts/PRD-EXPLICADO-PARA-HUMANOS-TONTOS.md) | Reference — plain Spanish explanation of pipeline stages | |
| [implementation-readiness-report.md](../../../_bmad-output/planning-artifacts/implementation-readiness-report.md) | Reference — readiness assessment for implementation | |
| [project-context.md](../../../_bmad-output/project-context.md) | Reference — AI agent project context | |

### Technical Research
| Document | Relevance | Location |
|----------|-----------|----------|
| [technical-research-ralph-dspy-compatibility.md](../../../_bmad-output/planning-artifacts/research/aegf-technology-validation-research-2026-04-22.md) | **Primary** — DSPy compatibility research, Ralph Loop analysis | |

### Brainstorming (decision rationale)
| Document | Relevance | Location |
|----------|-----------|----------|
| [aegf-dspy-langgraph-brief.md](../../../_bmad-output/brainstorming/aegf-dspy-langgraph-brief.md) | Reference — brainstorm brief | |
| [aegf-dspy-langgraph-distillate.md](../../../_bmad-output/brainstorming/aegf-dspy-langgraph-distillate.md) | Reference — distilled insights | |
| [brainstorming-deep-validation-2026-04-21.md](../../../_bmad-output/brainstorming/brainstorming-deep-validation-2026-04-21.md) | Reference — validation session | |
| [brainstorming-session-2026-04-21-dspy-langgraph-aegf.md](../../../_bmad-output/brainstorming/brainstorming-session-2026-04-21-dspy-langgraph-aegf.md) | Reference — session notes | |
| [mary-decision-summary-dspy-langgraph-aegf.md](../../../_bmad-output/brainstorming/mary-decision-summary-dspy-langgraph-aegf.md) | **Primary** — key decision rationale | |
| [murat-test-architect-dspy-aegf.md](../../../_bmad-output/brainstorming/murat-test-architect-dspy-aegf.md) | Reference — test architect perspective | |
| [research-dspy-langgraph-aegf-2026-04-21.md](../../../_bmad-output/brainstorming/research-dspy-langgraph-aegf-2026-04-21.md) | **Primary** — technical research findings | |
| [technical-research-dspy-langgraph.md](../../../_bmad-output/brainstorming/technical-research-dspy-langgraph.md) | **Primary** — tech stack research | |

### Innovation
| Document | Relevance | Location |
|----------|-----------|----------|
| [innovation-strategy-2026-04-22.md](../../../_bmad-output/innovation/innovation-strategy-2026-04-22.md) | Reference — strategic context | |

### Implementation
| Document | Relevance | Location |
|----------|-----------|----------|
| [sprint-status.yaml](../../../_bmad-output/implementation-artifacts/sprint-status.yaml) | **Primary** — story tracking, status, dependency map | v2.0 |
| [sprint-status-plan.md](../../../_bmad-output/implementation-artifacts/sprint-status-plan.md) | Reference — sprint planning | |

---

## Story-to-Spec Mapping

| BMAD Story | Smart Ralph Spec | Epic.md Section | Size |
|------------|------------------|-----------------|------|
| 0.1 Baseline Measurement Infrastructure | `baseline-measurement` | Spec 1 | S |
| 0.2 Prompt Externalization Setup | `prompt-externalization` | Spec 2 | XS |
| 0.3 Anchor Dataset Creation | `anchor-dataset` | Spec 3 | L |
| 0.4 Dependency Compatibility | `dependency-compatibility` | Spec 4 | XS |

## NFRs Covered by Epic 0

| NFR | How Epic 0 Covers It |
|-----|----------------------|
| NFR-001: Test Coverage >=90% | Epic 1 will add tests; Epic 0 sets up test infrastructure |
| NFR-002: Spearman >0.8 | Story 0.1 measures baseline for NFR-002 |
| NFR-007: MIPROv2 compile <= 3x baseline | Story 0.1 measures baseline for NFR-007 |
| NFR-009: Rollback <1 min | Story 0.1 verifies rollback time |

## Key Evidence from Codebase (in Product Brief)

The following hardcoded prompt locations were verified in the Product Brief and are addressed by Epic 0:

| File | Problem | Story |
|------|---------|-------|
| `src/factory/trajectory_generator.py:63` | Spanish template: `"Razonamiento: {reasoning}"` | 0.2 |
| `src/factory/hard_query_builder.py:214` | Hardcoded Spanish category→objective mapping | 0.2 |
| `src/audit/judge.py:149` | Hardcoded YAML prompts | 0.2 |
| `src/audit/calibration.py:47` | Brute-force grid search (no Bayesian optimization) | 0.1, 0.4 |
| `scripts/benchmark/measure_performance.py:34` | `numpy` used but NOT in requirements.txt | 0.4 (BUG FIX) |

## Dependencies on Other Epics

Epic 0 is the FIRST epic in the sequence. Its output feeds:
- **Epic 1 (DSPy Integration):** Depends on Story 0.2 (prompts), 0.3 (anchors), 0.4 (deps)
- **Epic 2 (Dataset Pipeline):** Indirectly via Epic 1's output
- **Epic X (Integration Gate):** Depends on ALL of Epic 0, 1, 2
- **Epic 3 (LangGraph):** Depends on Epic X gate passing
