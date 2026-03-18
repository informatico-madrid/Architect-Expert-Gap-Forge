# Experimentation Pipeline Checklist: Project Maintenance

**Purpose**: Validate requirements quality for rapid experimentation workflow
**Created**: 2026-03-18
**Feature**: [specs/006-project-maintenance/spec.md](specs/006-project-maintenance/spec.md)

## Requirement Completeness

- [ ] CHK001 - Are all 5 new files explicitly listed for creation? [Completeness, Spec §FR-007, §FR-008, §FR-009, §FR-010, §FR-011]
  - src/research/train_tokenizer.py
  - src/audit/eval_bpb.py
  - src/research/experiment_orchestrator.py
  - docs/experiments.md
  - configs/stage_4_training/axolotl/README.md
- [ ] CHK002 - Is the current state (0/5 files exist) documented? [Completeness, Spec §FR-007]
- [ ] CHK003 - Are parametrized dataset variants specified (dedup_threshold, gold_injection_rate, etc.)? [Completeness, Spec §FR-012]
- [ ] CHK004 - Is structured result registration specified (TSV/DB)? [Completeness, Spec §FR-013]

## Requirement Clarity

- [ ] CHK005 - Is "fast-mode" quantified with specific metrics (<30 minutes)? [Clarity, Spec §SC-006]
- [ ] CHK006 - Is the experiment loop (generate → tokenize → train → evaluate → report) explicit? [Clarity, User Story 4]
- [ ] CHK007 - Are all metrics (val_bpb, peak_vram_mb, mfu_percent, total_tokens_M) enumerated? [Clarity, User Story 4]
- [ ] CHK008 - Is the comparison capability (10 variants in <5 minutes) quantified? [Clarity, Spec §SC-007]

## Requirement Consistency

- [ ] CHK009 - Do all 5 files align with the rapid experimentation goal? [Consistency, User Story 4]
- [ ] CHK010 - Are parametrized variants consistent across train_tokenizer and experiment_orchestrator? [Consistency, Spec §FR-012]
- [ ] CHK011 - Are result formats (TSV/DB) consistent between orchestrator and documentation? [Consistency, Spec §FR-013]

## Acceptance Criteria Quality

- [ ] CHK012 - Can experiment loop completion time be objectively measured (<30 minutes)? [Measurability, Spec §SC-006]
- [ ] CHK013 - Can 10 variant comparison be measured (<5 minutes)? [Measurability, Spec §SC-007]
- [ ] CHK014 - Can first experiment execution time be measured (<10 minutes)? [Measurability, Spec §SC-008]
- [ ] CHK015 - Is the structured report format (TSV/DB) specified? [Measurability, Spec §FR-013]

## Scenario Coverage

- [ ] CHK016 - Are requirements defined for researcher testing new dataset configuration? [Coverage, User Story 4]
- [ ] CHK017 - Are requirements defined for experiment result reporting? [Coverage, User Story 4]
- [ ] CHK018 - Are requirements defined for comparing multiple variants? [Coverage, User Story 4]
- [ ] CHK019 - Are requirements defined for fast-mode vs normal-mode? [Coverage, Gap]

## Edge Case Coverage

- [ ] CHK020 - Is behavior specified when tokenizer training fails? [Edge Case, Spec §Edge Cases]
- [ ] CHK021 - Is behavior specified when experiment runs out of disk space? [Edge Case, Spec §Edge Cases]
- [ ] CHK022 - Is behavior specified when dataset has insufficient data? [Edge Case, Gap]
- [ ] CHK023 - Is checkpoint resume functionality specified? [Edge Case, Spec §Edge Cases]

## Dependencies & Assumptions

- [ ] CHK024 - Are dependencies on Axolotl validated? [Dependency, Spec §FR-011]
- [ ] CHK025 - Are dependencies on vLLM for evaluation validated? [Dependency, User Story 4]
- [ ] CHK026 - Is the assumption that BPB is a cheap metric validated? [Assumption, User Story 4]
- [ ] CHK027 - Are dependencies on tokenizer compatibility documented? [Dependency, Spec §FR-011]

## Non-Functional Requirements

- [ ] CHK028 - Is performance requirement (<30 minutes for full loop) specified? [NFR, Spec §SC-006]
- [ ] CHK029 - Is efficiency requirement (<5 minutes for 10 variants) specified? [NFR, Spec §SC-007]
- [ ] CHK030 - Is developer experience impact measured (rapid iteration vs hours/days)? [NFR, User Story 4]
- [ ] CHK031 - Is cost control addressed (cheap metrics vs expensive training)? [NFR, User Story 4]

## Ambiguities & Conflicts

- [ ] CHK032 - Is there any ambiguity about what constitutes "fast-mode"? [Ambiguity, Gap]
- [ ] CHK033 - Are there any conflicts between parametrized variants and Axolotl config? [Conflict, Gap]
- [ ] CHK034 - Is the tokenizer compatibility guidance (3 options) complete? [Ambiguity, Spec §FR-011]
- [ ] CHK035 - Is the result registration format (TSV vs DB) specified? [Ambiguity, Spec §FR-013]

## Notes

- Check items off as completed: `[x]`
- Add comments or findings inline
- Link to relevant resources or documentation
- Items are numbered sequentially for easy reference
