# Prompt & Doctrine Requirements Quality Checklist: PHPLegacyDriver

**Purpose**: Validate completeness and clarity of Teacher prompt template, doctrine file, and 3-section output schema requirements
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md)

## Prompt Template Requirements

- [ ] CHK001 — Are all required template keys (`system.php_legacy.base`, `system.php_legacy.doctrine`, `user.php_legacy.fragment`, etc.) explicitly enumerated? [Completeness, Spec §FR-020]
- [ ] CHK002 — Is the template variable set (`${fragment}`, `${legacy_signatures}`, `${platform}`, `${blueprint}`, `${governance}`) fully listed? [Completeness, Spec §FR-022]
- [ ] CHK003 — Is the relationship between `_prompt("system.php_legacy.base")` routing and profile detection defined? [Clarity, Gap]
- [ ] CHK004 — Are requirements defined for template fallback when platform-specific doctrine is unavailable? [Edge Case, Gap]
- [ ] CHK005 — Is the taxonomy YAML structure for PHP templates specified (standalone file vs nested in existing taxonomy)? [Clarity, Spec §FR-020]

## 3-Section Output Schema

- [ ] CHK006 — Are the 3 mandatory output sections (DEBT_DIAGNOSTIC, MODERN_PROPOSAL, MAPPING_LOGIC) defined with exhaustive content requirements? [Completeness, Spec §FR-021]
- [ ] CHK007 — Is the DEBT_DIAGNOSTIC section required to include a SEVERITY classification? [Clarity, Contract §prompt-schema]
- [ ] CHK008 — Is MODERN_PROPOSAL required to target PHP 8.1+ syntax specifically? [Clarity, Contract §prompt-schema]
- [ ] CHK009 — Is MAPPING_LOGIC required to reference specific elements from the input fragment? [Completeness, Contract §prompt-schema]
- [ ] CHK010 — Are section delimiters (`[DEBT_DIAGNOSTIC]`, `[MODERN_PROPOSAL]`, `[MAPPING_LOGIC]`) specified with exact regex for parsing? [Clarity, Spec §FR-021]
- [ ] CHK011 — Are requirements defined for Teacher output that includes extra sections beyond the 3 required ones? [Edge Case, Gap]

## Doctrine & Master File

- [ ] CHK012 — Is the master Symfony hexagonal doctrine file content specified with minimum required patterns (Ports, Adapters, DTOs, DI)? [Completeness, Spec §FR-023]
- [ ] CHK013 — Are the Symfony components referenced in FR-023 (Doctrine ORM, DI Container, Event Dispatcher) versioned or unversioned? [Clarity, Spec §FR-023]
- [ ] CHK014 — Is the injection mechanism for master doctrine into system prompt defined (via `${governance}` or separate variable)? [Clarity, Gap]
- [ ] CHK015 — Are requirements defined for doctrine updates when target framework evolves (Symfony 7, PHP 8.4)? [Gap]

## Context Enrichment

- [ ] CHK016 — Is the complete set of enrichment data for Teacher prompts listed (LEGACY_SIGNATURES, LEGACY_ACTION, IMPLICIT_DEPS, preamble)? [Completeness, Spec §FR-022]
- [ ] CHK017 — Is the order of context injection (system prompt first, then user prompt with fragment + signatures) explicitly specified? [Clarity, Gap]
- [ ] CHK018 — Are token budget requirements defined for the combined prompt (doctrine + signatures + fragment + preamble)? [Gap]
- [ ] CHK019 — Is the behavior specified when combined context exceeds the Teacher model's context window? [Edge Case, Gap]

## Quality Validation

- [ ] CHK020 — Is SC-009 (≥90% of Teacher outputs follow 3-section schema) measurable with a specific validation method? [Measurability, Spec §SC-009]
- [ ] CHK021 — Are requirements defined for what "structural parsing" of Teacher output means (regex, section markers, LLM judge)? [Clarity, Spec §SC-009]
- [ ] CHK022 — Are requirements defined for handling Teacher outputs that fail schema validation? [Edge Case, Gap]

## Notes

- Contract prompt-schema.md provides detailed examples but spec FR-021 is more abstract — cross-reference consistency needed
- FR-022 lists enrichment data but doesn't specify maximum sizes or truncation behavior
- No requirements exist for A/B testing or iterating on prompt quality
