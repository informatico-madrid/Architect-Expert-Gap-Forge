---
name: aegf-dataset-training
goal: Create dataset mixing pipeline, implement agentic preservation of legacy knowledge, and extend training to TypeScript/YAML/Jinja domains — enabling the model to handle multi-language migrations beyond Python/PHP.
version: 1.0
date: 2026-04-29
status: planning
storyCount: 3
specs:
  - 001-dataset-mixing
  - 002-agentic-preservation
  - 003-multi-language-training
---

# Epic: aegf-dataset-training

## Epic Goal

Build the Dataset & Training Pipeline (Epic 2) that transforms anchor dataset samples into optimized training data, preserves agentic knowledge during transformation, and extends the model to handle TypeScript, YAML, and Jinja migration tasks alongside existing Python/PHP coverage.

## BMAD Sources

This epic is decomposed from **BMAD Epic 2: Dataset & Training Pipeline** (`_bmad-output/planning-artifacts/epics.md` v4.0).
All 3 stories, acceptance criteria, and user outcomes are sourced directly from the BMAD epics document.

| BMAD Document | Role in This Epic |
|---------------|-------------------|
| [epics.md](../../../_bmad-output/planning-artifacts/epics.md) | **Primary** — story definitions (2.1-2.3), AC, dependencies |
| [aegf-3-layer-prd.md](../../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) | NFR-002 (Spearman > 0.8), NFR-007 (MIPROv2 compile), NFR-003 (multi-language) |
| [architecture.md](../../../_bmad-output/planning-artifacts/architecture.md) | 2-layer architecture context, training pipeline position |
| [sprint-status.yaml](../../../_bmad-output/implementation-artifacts/sprint-status.yaml) | Story tracking |

### Story References (epics.md line numbers)

| Story | epics.md Reference | Smart Ralph Spec |
|-------|-------------------|------------------|
| 2.1 Dataset Mixing | `epics.md:517` | `specs/001-dataset-mixing/plan.md` |
| 2.2 Agentic Preservation | `epics.md:543` | `specs/002-agentic-preservation/plan.md` |
| 2.3 Multi-Language Training | `epics.md:559` | `specs/003-multi-language-training/plan.md` |

## Smart Ralph Mapping

BMAD defines 3 stories in Epic 2. Smart Ralph creates 1 spec per story following the Epic 0 pattern:

| BMAD Story | Spec Directory | plan.md Status |
|------------|---------------|----------------|
| 2.1 Dataset Mixing | `001-dataset-mixing/` | plan.md created (pending) |
| 2.2 Agentic Preservation | `002-agentic-preservation/` | plan.md created (pending) |
| 2.3 Multi-Language Training | `003-multi-language-training/` | plan.md created (pending) |

## Scope

### IN Scope

- Dataset mixing pipeline that combines anchor samples with evolved examples
- Agentic preservation layer that tracks and preserves knowledge during training
- Multi-language training extension for TypeScript, YAML, and Jinja
- Performance parity between multi-language and Python/PHP migrations

### OUT of Scope

- LangGraph state machine (Epic 3)
- Integration gate validation (Epic 2.5)
- Actual model training runs (triggered externally after pipeline is ready)
- Production deployment infrastructure

## Dependencies

**Prerequisites (from Epic 0):**
- Spec 3: anchor-dataset (anchor samples exist)
- Spec 4: dependency-compatibility (datasets library version pinned)

**Prerequisites (from Epic 1):**
- dspy-integration (DSPy Signatures defined for trajectory/judge/calibration)

**Gate Dependency:**
- Epic 2.5 (Integration Gate) must pass before Epic 3 can begin

**Execution Order:**
- 2.1 → 2.2 → 2.3 (sequential — each builds on the previous)

## Interface Contracts

### Dataset Mixing
- **Writes:** `src/training/dataset_mixer.py`, `configs/training/mix_config.yaml`
- **Reads:** `datasets/anchors/v1/anchor_dataset.jsonl` (anchor samples)
- **Output:** Mixed dataset in JSONL format with stratified domain distribution

### Agentic Preservation
- **Writes:** `src/training/agentic_preservation.py`, `src/training/knowledge_tracker.py`
- **Reads:** Training intermediate states, anchor dataset metadata
- **Output:** Knowledge preservation report with integrity scores

### Multi-Language Training
- **Writes:** `src/training/multi_language.py`, `configs/training/language_config.yaml`
- **Reads:** Mixed dataset from Dataset Mixing, language-specific patterns
- **Output:** Multi-language model weights or fine-tuning configuration

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Dataset mixing may reduce anchor quality if poorly stratified | HIGH | Use anchor manifest distribution as mixing baseline |
| Agentic preservation adds training overhead | MEDIUM | Profile early, make preservation checks configurable |
| Multi-language data may be scarce for TypeScript/Jinja | MEDIUM | Start with existing taxonomy coverage; expand if needed |
| Integration Gate criteria may block progress | HIGH | Monitor gate criteria throughout Epic 2 execution |

---

## Integration Gate (Epic 2.5)

**Note:** Epic X (Integration Gate) was moved out of Epic 2 by Winston during BMAD v4.0 restructure to resolve a circular dependency. While it gates Epic 3, it is conceptually part of Epic 2's output — it validates that Epic 2 stories meet acceptance criteria.

The Integration Gate spec exists as `specs/004-eic-integration-gate/plan.md` and is documented as **Epic 2.5** to reflect its position between Epic 2 and Epic 3.
