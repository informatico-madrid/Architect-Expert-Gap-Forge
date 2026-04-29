# Spec: anchor-dataset

**Epic:** specs/_epics/aegf-infrastructure/epic.md
**Size:** L (1 builder script + 2 data files + fixtures. Human verification is the bottleneck: ~100-200 human-hours)
**Status:** pending (blocked on: baseline-measurement, prompt-externalization)

## BMAD Source

- **Story:** 0.3 — Anchor Dataset Creation (NEW in v4.0, Party Mode consensus 4/4)
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:255`](../../_bmad-output/planning-artifacts/epics.md#story-03-anchor-dataset-creation-nueva-v40)
- **PRD:** [aegf-3-layer-prd.md](../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) — FR-009 (Anchor Dataset Creation)
- **Product Brief:** [aegf-autonomous-forge-product-brief.md](../../_bmad-output/planning-artifacts/aegf-autonomous-forge-product-brief.md) — MIPROv2 bootstrap context
- **Sprint Status:** [sprint-status.yaml](../../_bmad-output/implementation-artifacts/sprint-status.yaml) — story 0.3, status: backlog
- **Party Mode Note:** CRITICAL path item — without anchors, MIPROv2 compiles to vacuum. Party Mode v4.0 Change C1 (severity 9/10, 4/4 consensus)
- **PRD Explicado:** [PRD-EXPLICADO-PARA-HUMANOS-TONTOS.md](../../_bmad-output/planning-artifacts/PRD-EXPLICADO-PARA-HUMANOS-TONTOS.md) — Stage 2 Factory section (why trajectories need anchor data)

## Goal

As an ML Engineer, I want a domain-specific anchor dataset of 100-200 samples with ground truth labels, so that DSPy MIPROv2 can compile and optimize signatures effectively.

## Acceptance Criteria

1. **Anchor samples generated:** Running `infrastructure/anchor_dataset_builder.py` produces 100-200 samples with:
   - Input: `domain_context`, `difficulty`, `turn_count`, `legacy_pattern`
   - Expected output: `trajectory`, `tool_usage_patterns` (for TrajectorySignature)
   - Expected output: `coherence`, `overall` (for JudgeSignature)
   - Expected output: `optimized_parameters`, `quality_score` (for CalibrationSignature)

2. **Domain distribution:** Samples cover domains matching existing taxonomy structure:
   - Home Assistant (Python/HA-YAML/Jinja) -- 40%
   - PHP Legacy (oscommerce, wordpress, zencart, symfony) -- 30%
   - Generic domain (Python/PHP) -- 20%
   - Other (YAML configs, HA addons) -- 10%

3. **Storage:** Data stored in `datasets/anchors/v1/anchor_dataset.jsonl` with metadata in `datasets/anchors/v1/anchor_manifest.json`.

4. **Manual verification:** Each sample includes ground truth labels marked as manually verified.

## Interface Contracts

### Writes
- `infrastructure/anchor_dataset_builder.py`
- `datasets/anchors/v1/anchor_dataset.jsonl`
- `datasets/anchors/v1/anchor_manifest.json`

### Reads
- `tests/fixtures/seed_examples.yaml` (seed data)
- `tests/fixtures/anchor_dataset_examples.json` (format reference)
- Baseline results from Spec: baseline-measurement
- External model API (OpenAI/Gemini/vLLM) -- external dependency

### JSONL Record Schema
```json
{
  "id": "anchor_001",
  "domain": "home_assistant",
  "difficulty": "easy",
  "turn_count": 4,
  "legacy_pattern": "string",
  "domain_context": "string",
  "expected_trajectory": "string",
  "expected_tool_usage_patterns": ["string"],
  "expected_coherence": 0.85,
  "expected_overall": 0.80,
  "expected_optimized_parameters": {},
  "expected_quality_score": 0.82,
  "verified": true,
  "verified_by": "string"
}
```

### Manifest Schema
```json
{
  "version": "v1",
  "created": "ISO8601",
  "total_samples": 50,
  "domain_distribution": {"home_assistant": 20, "php_legacy": 15, "generic_domain": 10, "other": 5},
  "difficulty_distribution": {"easy": 10, "medium": 25, "hard": 15}
}
```
(v0.1 targets 50 samples; v0.2 scales to 100-200)

## Dependencies

- **Spec: baseline-measurement** -- needs baseline scores to validate anchor quality
- **Spec: prompt-externalization** -- needs English prompts for generating anchor trajectories

## Implementation Notes

- `infrastructure/` directory must be created (Spec: baseline-measurement also writes here)
- Seed data exists: `tests/fixtures/seed_examples.yaml` (13 seeds), `tests/fixtures/calibration_examples.json` (5 examples), `tests/fixtures/anchor_dataset_examples.json` (format fixtures)
- Reference corpus: `tests/fixtures/reference_corpus/homeassistant/` contains 5 repos
- **TAXONOMY CONSTRAINT:** Only `home_assistant`, `php_legacy`, and `generic_domain` taxonomies exist. No TypeScript taxonomy.
- Each anchor sample requires manual verification -- intellectual property, not auto-generated
- Party Mode consensus (4/4): CRITICAL path item. Without anchors, MIPROv2 compiles to vacuum.
- Generation requires external model inference (OpenAI/Gemini/vLLM) -- external dependency
- **HUMAN BOTTLENECK:** 100-200 manually verified samples = ~100-200 human-hours
- **PHASED APPROACH:** v0.1 = 50 samples (minimum viable for MIPROv2 bootstrap), v0.2 = 100-200 samples
