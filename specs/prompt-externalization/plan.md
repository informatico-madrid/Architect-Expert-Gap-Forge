# Spec: prompt-externalization

**Epic:** specs/_epics/aegf-infrastructure/epic.md
**Size:** XS (< 1 day)
**Status:** pending (no dependencies)

## BMAD Source

- **Story:** 0.2 — Prompt Externalization Setup
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:230`](../../_bmad-output/planning-artifacts/epics.md#story-02-prompt-externalization-setup)
- **PRD:** [aegf-3-layer-prd.md](../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) — FR-008 (Prompts Migration), Section 2.2 (hardcoded prompt evidence)
- **Product Brief:** [aegf-autonomous-forge-product-brief.md](../../_bmad-output/planning-artifacts/aegf-autonomous-forge-product-brief.md) — hardcoded prompt evidence table (line 63, 182 in trajectory_generator.py, 214 in hard_query_builder.py, 149 in judge.py)
- **Architecture:** [architecture.md](../../_bmad-output/planning-artifacts/architecture.md) — 2-layer structure, DSPy integration context
- **Sprint Status:** [sprint-status.yaml](../../_bmad-output/implementation-artifacts/sprint-status.yaml) — story 0.2, status: backlog
- **PRD Explicado:** [PRD-EXPLICADO-PARA-HUMANOS-TONTOS.md](../../_bmad-output/planning-artifacts/PRD-EXPLICADO-PARA-HUMANOS-TONTOS.md) — Stage 2 Factory section (prompt hard-coding problem)

## Goal

As an ML Engineer, I want existing taxonomy prompts cataloged and mirrored into `.example.yaml` template files with English translations, so that DSPy can manage them as language-agnostic external configuration.

## Acceptance Criteria

1. **Catalog and template prompts:** Running the spec creates 4 `.example.yaml` files with English prompt translations:
   - `src/factory/prompts_trajectory.example.yaml`
   - `src/factory/prompts_hard_query.example.yaml`
   - `src/audit/prompts_judge.example.yaml`
   - `src/audit/prompts_calibration.example.yaml`

2. **Preserve functionality:** Existing functionality is preserved and Spearman correlation > 0.8 with existing judge.py scores (no regression).

3. **Coexistence with taxonomy:** `.example.yaml` files coexist without conflict with existing taxonomy YAMLs (taxonomy is for Stage 2; `.example.yaml` is for DSPy).

## Interface Contracts

### Writes
- 4 `.example.yaml` files under `src/factory/` and `src/audit/`

### Reads
- `src/factory/prompt_builder.py` (taxonomy keys)
- Existing taxonomy YAMLs: `configs/stage_2_factory/taxonomy/*/prompts_taxonomy.yaml`
- `src/audit/judge.py` (via PromptManager loading `eval_prompts.yaml`)
- `src/audit/calibration.py` (via `load_calibration_prompts_from_yaml`)

### YAML Schema per File
```yaml
prompts:
  <prompt_key>:
    system: "<english prompt text with $placeholders>"
    user: "<english user prompt with $placeholders>"
```

### Naming Convention
`<module>.example.yaml` -- `.example` suffix signals "template, copy and customize"

## Dependencies

- **None** (can start immediately, parallel with Spec: dependency-compatibility)

## Implementation Notes

- Prompts are ALREADY externalized in YAML taxonomy files -- NOT hardcoded in Python
- Task is to: (1) catalog existing prompts from taxonomy YAMLs, (2) translate to English, (3) create `.example.yaml` template files for DSPy consumption
- No `.example.yaml` files exist anywhere in the codebase -- new naming convention
- Current prompts are in Spanish; English translation is part of the scope
- Some taxonomy keys may be broken (e.g., `system.php_legacy.context` references a non-existent taxonomy) -- note as issues
- Calibration prompts loaded from `configs/stage_5_evaluation/calibration_prompts.yaml`
- Judge prompts loaded from `configs/stage_5_evaluation/eval_prompts.yaml`
- Hard query templates from `configs/stage_2_factory/prompts/hard_query_templates.yaml`
- Trajectory templates from `configs/stage_2_factory/prompts/trajectory_templates.yaml`
