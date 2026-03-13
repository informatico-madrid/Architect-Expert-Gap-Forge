# Performance Requirements Quality Checklist: PHPLegacyDriver

**Purpose**: Validate completeness and clarity of performance, chunking, and scaling requirements
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md)

## Performance Targets

- [ ] CHK001 — Is the <5 second/file target (SC-001) specified with hardware baseline (CPU, RAM, disk type)? [Measurability, Spec §SC-001]
- [ ] CHK002 — Is the 2000+ line file threshold for SC-001 representative of actual PHP files in `data/raw/multi_legacy/`? [Clarity, Spec §SC-001]
- [ ] CHK003 — Are performance requirements defined for repository-level processing (total time for N files)? [Coverage, Gap]
- [ ] CHK004 — Is memory consumption specified or bounded for processing large PHP files? [Gap]
- [ ] CHK005 — Are performance requirements defined for IncludeGraph construction across an entire repository? [Coverage, Gap]

## Chunking & Large Files

- [ ] CHK006 — Is the "maximum fragment size compatible with context window" quantified with a specific token/character count? [Clarity, Spec §FR-011]
- [ ] CHK007 — Is the 10,000-line threshold for automatic chunking specified as configurable? [Clarity, Spec Edge Cases]
- [ ] CHK008 — Are requirements defined for chunking overhead (number of chunks generated per large file)? [Gap]
- [ ] CHK009 — Is the overlap strategy for fallback chunking (50-line chunks with 5-line overlap per research.md) specified in the spec? [Ambiguity, Gap]
- [ ] CHK010 — Are requirements defined for the case where sub-chunking a 500+ line `case` block produces fragments too small to be useful? [Edge Case, Spec §FR-019]

## Scaling

- [ ] CHK011 — Are requirements defined for processing all 7 repositories in `data/raw/multi_legacy/` in a single run? [Coverage, Gap]
- [ ] CHK012 — Is the total expected bundle count per repository estimated or bounded? [Gap]
- [ ] CHK013 — Are disk space requirements for generated bundles specified? [Gap]
- [ ] CHK014 — Is synchronous processing (SC-001) explicitly chosen over async, with rationale documented? [Clarity, Spec §SC-001]

## Notes

- SC-001 says "síncrono" — but ProcessingConfig and existing pipeline use async patterns
- Research R-003 specifies "50 líneas con overlap de 5" but this detail is not in spec FR-017
