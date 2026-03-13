# Extraction Requirements Quality Checklist: PHPLegacyDriver

**Purpose**: Validate completeness and clarity of core PHP extraction and fragmentation requirements
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 — Are all 6 fragment types (function, class, switch_block, bootstrap, mixed_html, catchall) explicitly defined with extraction criteria? [Completeness, Spec §FR-017]
- [ ] CHK002 — Are extraction rules specified for nested PHP constructs (functions inside classes, functions inside if/else)? [Coverage, Gap]
- [ ] CHK003 — Is the regex pattern for function detection (`^\s*function\s+(\w+)\s*\(`) documented with its limitations? [Clarity, Spec §FR-002]
- [ ] CHK004 — Are extraction criteria defined for anonymous functions / closures in hybrid PHP code? [Coverage, Gap]
- [ ] CHK005 — Is the behavior specified when a single `.php` file contains multiple classes? [Coverage, Gap]
- [ ] CHK006 — Are the brace-matching rules for fragment boundary detection explicitly documented? [Clarity, Spec §FR-017]

## Requirement Clarity

- [ ] CHK007 — Is "significant `<?php ?>` block" quantified with specific criteria (minimum lines, token count)? [Clarity, Spec §FR-017]
- [ ] CHK008 — Is "overlap de contexto" in fallback chunking quantified (5 lines stated in research.md but not in spec)? [Ambiguity, Spec §FR-017]
- [ ] CHK009 — Is the 500-line threshold for case sub-chunking justified and is it configurable? [Clarity, Spec §FR-019]
- [ ] CHK010 — Is "bloque de lógica PHP" distinguished from PHP template code (`<?= $var ?>`) with measurable criteria? [Clarity, Spec §FR-008]

## Preamble Rule Coverage

- [ ] CHK011 — Is the Preamble Rule (FR-018) defined with specific criteria for what constitutes the "bloque de setup inicial"? [Clarity, Spec §FR-018]
- [ ] CHK012 — Is the preamble attachment mechanism specified: virtual copy, reference, or inline inclusion? [Ambiguity, Spec §FR-018]
- [ ] CHK013 — Are requirements defined for files where the preamble IS the entire file (no functions/classes)? [Edge Case, Spec §FR-018]
- [ ] CHK014 — Is preamble size limit defined to prevent oversized context injection? [Gap]

## LEGACY_ACTION Labeling

- [ ] CHK015 — Are the 6 LEGACY_ACTION categories (DB_ACCESS, ROUTING, AUTH_SESSION, OUTPUT_RENDER, FILE_IO, BUSINESS_LOGIC) defined with unambiguous assignment criteria? [Clarity, Spec §FR-019]
- [ ] CHK016 — Is the behavior specified when a fragment matches multiple LEGACY_ACTION categories? [Ambiguity, Spec §FR-019]
- [ ] CHK017 — Is "exactly one category" (FR-003 says "exactamente una categoría semántica") reconciled with data-model's `semantic_label` which is singular? [Consistency, Spec §FR-003]

## Edge Case Coverage

- [ ] CHK018 — Are requirements defined for PHP files with syntax errors (unclosed braces, missing semicolons)? [Edge Case, Gap]
- [ ] CHK019 — Are requirements defined for PHP files using alternative syntax (`if/endif`, `while/endwhile`)? [Coverage, Gap]
- [ ] CHK020 — Is behavior specified for PHP files that consist entirely of `define()` constants with no functions? [Edge Case, Gap]
- [ ] CHK021 — Are requirements defined for heredoc/nowdoc strings that contain PHP-like syntax? [Edge Case, Gap]
- [ ] CHK022 — Is the fallback behavior specified when regex fragmentation produces zero fragments from a non-empty PHP file? [Edge Case, Gap]

## Notes

- Spec §FR-003 lists 6 categories (PERSISTENCE, STATE, MODULE_LINK, SECURITY_SMELL, CONSTANT_DEF, MODERN_REFERENCE) while data-model.md lists different 6 (DB_ACCESS, ROUTING, AUTH_SESSION, OUTPUT_RENDER, FILE_IO, BUSINESS_LOGIC) — potential inconsistency flagged in CHK015/CHK017
- Research R-003 provides more detail on fragmentation strategy than the spec itself
