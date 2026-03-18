# Backend Configuration Checklist: Project Maintenance

**Purpose**: Validate requirements quality for default inference backend configuration
**Created**: 2026-03-18
**Feature**: [specs/006-project-maintenance/spec.md](specs/006-project-maintenance/spec.md)

## Requirement Completeness

- [ ] CHK001 - Are all backend configuration locations specified? [Completeness, Spec §FR-003, §FR-004]
  - src/audit/config.py: DEFAULT_PROFESSOR_BACKEND
  - configs/stage_5_evaluation/eval_config.yaml: professor_backend
  - Environment variable support: AEGF_PROFESSOR_BACKEND
- [ ] CHK002 - Is the default value "vllm" specified in all locations? [Completeness, Spec §FR-003, §FR-004]
- [ ] CHK003 - Is the override mechanism (environment variable) documented? [Completeness, Spec §FR-005]
- [ ] CHK004 - Is the current problematic behavior ("auto") documented? [Completeness, Spec §FR-003]

## Requirement Clarity

- [ ] CHK005 - Is "auto" selection behavior explicitly described as problematic? [Clarity, Spec §FR-003]
- [ ] CHK006 - Is the line number reference (src/audit/config.py:140) provided? [Clarity, Spec §FR-003]
- [ ] CHK007 - Is the config file path (configs/stage_5_evaluation/eval_config.yaml:21) specified? [Clarity, Spec §FR-004]
- [ ] CHK008 - Is the environment variable name (AEGF_PROFESSOR_BACKEND) explicit? [Clarity, Spec §FR-005]

## Requirement Consistency

- [ ] CHK009 - Do both config locations specify "vllm" as default? [Consistency, Spec §FR-003, §FR-004]
- [ ] CHK010 - Is the override mechanism consistent across all locations? [Consistency, Spec §FR-005]
- [ ] CHK011 - Are acceptance scenarios aligned with functional requirements? [Consistency, User Story 2]

## Acceptance Criteria Quality

- [ ] CHK012 - Can "uses vLLM by default" be objectively verified? [Measurability, Spec §SC-003]
- [ ] CHK013 - Can CI runs without GOOGLE_API_KEY be tested? [Measurability, User Story 2]
- [ ] CHK014 - Can override to Gemini be verified with environment variable? [Measurability, User Story 2]
- [ ] CHK015 - Is "100% of CI runs" measurable? [Measurability, Spec §SC-003]

## Scenario Coverage

- [ ] CHK016 - Are requirements defined for clean environment without GOOGLE_API_KEY? [Coverage, User Story 2]
- [ ] CHK017 - Are requirements defined for environment with GOOGLE_API_KEY set? [Coverage, User Story 2]
- [ ] CHK018 - Are requirements defined for developer wanting to use Gemini? [Coverage, User Story 2]
- [ ] CHK019 - Is the CI enforcement scenario covered? [Coverage, User Story 2]

## Edge Case Coverage

- [ ] CHK020 - Is behavior specified when both GOOGLE_API_KEY and AEGF_PROFESSOR_BACKEND are set? [Edge Case, Gap]
- [ ] CHK021 - Is behavior specified when evaluation pipeline is called without any config? [Edge Case, Gap]
- [ ] CHK022 - Is backward compatibility for existing users addressed? [Edge Case, Gap]
- [ ] CHK023 - Is error handling specified for invalid backend values? [Edge Case, Gap]

## Dependencies & Assumptions

- [ ] CHK024 - Are dependencies on vLLM installation validated? [Dependency, User Story 2]
- [ ] CHK025 - Is the assumption that CI uses local mocks confirmed? [Assumption, Constitution]
- [ ] CHK026 - Are dependencies on environment variable loading documented? [Dependency, Spec §FR-005]
- [ ] CHK027 - Is the assumption that GOOGLE_API_KEY controls Gemini usage validated? [Assumption, Spec §FR-003]

## Non-Functional Requirements

- [ ] CHK028 - Is security requirement (prevent accidental API calls) specified? [NFR, User Story 2]
- [ ] CHK029 - Is cost control requirement (prevent unexpected costs) documented? [NFR, User Story 2]
- [ ] CHK030 - Is developer experience impact measured (no accidental paid API usage)? [NFR, User Story 2]

## Ambiguities & Conflicts

- [ ] CHK031 - Is there any ambiguity about which backend is the default? [Ambiguity, Spec §FR-003]
- [ ] CHK032 - Are there any conflicts between config file and environment variable? [Conflict, Spec §FR-005]
- [ ] CHK033 - Is the migration path for existing users specified? [Ambiguity, Edge Cases]
- [ ] CHK034 - Is the timing of the change (immediate vs gradual) specified? [Ambiguity, Gap]

## Notes

- Check items off as completed: `[x]`
- Add comments or findings inline
- Link to relevant resources or documentation
- Items are numbered sequentially for easy reference
