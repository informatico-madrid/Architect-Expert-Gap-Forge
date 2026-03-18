# Formatting Checklist: Project Maintenance

**Purpose**: Validate requirements quality for canonical formatting tooling (ruff)
**Created**: 2026-03-18
**Feature**: [specs/006-project-maintenance/spec.md](specs/006-project-maintenance/spec.md)

## Requirement Completeness

- [ ] CHK001 - Are all three locations for ruff declaration specified? [Completeness, Spec §FR-001]
  - pyproject.toml
  - requirements-dev.txt
  - All documentation
- [ ] CHK002 - Is the exact version constraint `ruff>=0.9` specified? [Completeness, Spec §FR-002]
- [ ] CHK003 - Are both `make fmt` and `make lint` commands documented? [Completeness, User Story 1]
- [ ] CHK004 - Is the independent test scenario fully described? [Completeness, User Story 1]

## Requirement Clarity

- [ ] CHK005 - Is "canonical formatter" defined as ruff with specific version? [Clarity, Spec §FR-001]
- [ ] CHK006 - Is the installation command `pip install -r requirements-dev.txt` explicit? [Clarity, Spec §FR-002]
- [ ] CHK007 - Are the success metrics (<30 seconds for `make fmt`) quantified? [Clarity, Spec §SC-001]
- [ ] CHK008 - Is "zero style violations" measurable? [Clarity, Spec §SC-010]

## Requirement Consistency

- [ ] CHK009 - Does Makefile usage of ruff align with requirements-dev.txt specification? [Consistency, Spec §FR-001]
- [ ] CHK010 - Are all documentation references consistent with ruff as canonical tool? [Consistency]
- [ ] CHK011 - Do acceptance scenarios align with functional requirements? [Consistency, Spec §FR-001]

## Acceptance Criteria Quality

- [ ] CHK012 - Can `make fmt` be objectively measured for completion time (<30 seconds)? [Measurability, Spec §SC-001]
- [ ] CHK013 - Can `make lint` failure be objectively verified? [Measurability, Spec §SC-010]
- [ ] CHK014 - Is "clear error messages" in CI defined with specific format? [Clarity, User Story 1]
- [ ] CHK015 - Can new developer installation be verified in one command? [Measurability, User Story 1]

## Scenario Coverage

- [ ] CHK016 - Are requirements defined for unformatted code scenarios? [Coverage, User Story 1]
- [ ] CHK017 - Are requirements defined for PR with style violations? [Coverage, User Story 1]
- [ ] CHK018 - Are requirements defined for new developer setup? [Coverage, User Story 1]
- [ ] CHK019 - Is the CI enforcement scenario covered? [Coverage, User Story 1]

## Edge Case Coverage

- [ ] CHK020 - Is behavior specified when code is already formatted? [Edge Case, Gap]
- [ ] CHK021 - Is behavior specified for mixed style violations? [Edge Case, Gap]
- [ ] CHK022 - Is rollback/recovery specified if formatting breaks code? [Edge Case, Gap]
- [ ] CHK023 - Is behavior specified for files with existing comments? [Edge Case, Gap]

## Dependencies & Assumptions

- [ ] CHK024 - Are dependencies on ruff installation validated? [Dependency, Spec §FR-002]
- [ ] CHK025 - Is the assumption that Makefile already uses ruff confirmed? [Assumption, Spec §FR-001]
- [ ] CHK026 - Are dependencies on CI configuration documented? [Dependency, User Story 1]

## Non-Functional Requirements

- [ ] CHK027 - Is performance requirement (<30 seconds) specified for `make fmt`? [NFR, Spec §SC-001]
- [ ] CHK028 - Is developer experience impact measured (focus on writing code vs debating style)? [NFR, User Story 1]
- [ ] CHK029 - Is CI reliability impact addressed (no style debates)? [NFR, User Story 1]

## Ambiguities & Conflicts

- [ ] CHK030 - Is there any ambiguity about which style rules ruff should enforce? [Ambiguity, Gap]
- [ ] CHK031 - Are there any conflicts between existing Makefile and requirements-dev.txt? [Conflict, Spec §FR-001]
- [ ] CHK032 - Is the version constraint `>=0.9` justified with specific reasons? [Ambiguity, Spec §FR-002]

## Notes

- Check items off as completed: `[x]`
- Add comments or findings inline
- Link to relevant resources or documentation
- Items are numbered sequentially for easy reference
