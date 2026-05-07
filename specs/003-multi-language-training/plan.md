# Spec: multi-language-training

**Epic:** specs/_epics/aegf-dataset-training/epic.md
**Size:** M (3-5 days)
**Status:** pending (blocked on: dataset-mixing, agentic-preservation)

## BMAD Source

- **Story:** 2.3 — Multi-language Training Support
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:546`](../../_bmad-output/planning-artifacts/epics.md#story-23-multi-language-training-support)
- **PRD:** [aegf-3-layer-prd.md](../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) — FR-007 (Multi-language Training)

## Goal

As an ML Engineer, I want to train models on TypeScript, YAML, Jinja code in addition to Python/PHP, so that the model can handle diverse codebases.

## Acceptance Criteria

1. **Discovery correctness:** Given a TypeScript/YAML/Jinja repository, Stage 1 Discovery processes the files and extracts fragments using appropriate adapters.
2. **Language metadata:** Fragments include language-specific metadata.
3. **Multi-language training:** Stage 4 Training produces a model with multi-language capability.
4. **Performance parity:** When evaluated on TypeScript/YAML/Jinja migration tasks, the multi-language trained model's performance is comparable to Python/PHP migrations.

## Interface Contracts

### Reads
- TypeScript/TypeScript/Jinja repositories (via Stage 1 Discovery)
- Mixed dataset from Story 2.1

### Writes
- Model checkpoint with multi-language capability
- Evaluation results: `evaluation/multi_language_performance.json`

## Dependencies

- **Spec: dataset-mixing** (mixed dataset must exist)
- **Spec: agentic-preservation** (agentic benchmark infrastructure)
- Stage 1 Discovery must support TypeScript/YAML/Jinja adapters

## Implementation Notes

- Requires Stage 1 Discovery to support TypeScript/YAML/Jinja adapters (likely already exists)
- Performance comparison requires establishing a baseline on Python/PHP first
- Model training cost: high (same as Story 2.2)
