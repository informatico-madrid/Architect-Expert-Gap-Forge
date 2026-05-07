# Spec: dataset-mixing

**Epic:** specs/_epics/aegf-dataset-training/epic.md
**Size:** S (1-2 days)
**Status:** pending (blocked on: Epic 0 + Epic 1 complete)

## BMAD Source

- **Story:** 2.1 — Dataset Mixing with Hugging Face
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:505`](../../_bmad-output/planning-artifacts/epics.md#story-21-dataset-mixing-with-hugging-face)
- **PRD:** [aegf-3-layer-prd.md](../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) — FR-007 (Multi-language)
- **Product Brief:** [aegf-autonomous-forge-product-brief.md](../../_bmad-output/planning-artifacts/aegf-autonomous-forge-product-brief.md) — AR-006 (dataset mixing con HF)

## Goal

As an ML Engineer, I want to mix AEGF dataset with Hugging Face datasets, so that the model preserves agentic capability (tool usage).

## Acceptance Criteria

1. **Dataset mixing:** Running Stage 3 Curation with `dataset_mixer` config produces a combined dataset that preserves:
   - AEGF trajectories for migration patterns
   - HF datasets for agentic capability (tool usage)
   - Ratio: ~70% AEGF, ~30% HF (configurable)
2. **Deduplication:** The combined dataset has exact duplicates removed.
3. **Quality filter:** Samples below the LDI threshold are removed from the combined dataset.

## Interface Contracts

### Writes
- Stage 3 Curation `dataset_mixer` config module

### Writes (runtime data)
- Combined dataset (JSONL/Arrow format)

### Reads
- AEGF dataset (Stage 2 output, 4-turn trajectories)
- Hugging Face datasets: `ultrafeedback`, `camel`

## Dependencies

- **Epic 0** complete (baseline, anchors, prompts externalized, deps compatible)
- **Epic 1** complete (DSPy signatures defined and integrated)
- **Spec: dependency-compatibility** (datasets Hugging Face must be installed)

## Implementation Notes

- Hugging Face `datasets` library is used for loading HF datasets
- Dataset mixing ratio is configurable (default 70/30)
- Deduplication can be exact-string or semantic (start with exact)
- Quality filter uses LDI score threshold (value TBD from baseline)
