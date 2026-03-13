# Integration Requirements Quality Checklist: PHPLegacyDriver

**Purpose**: Validate completeness and clarity of Stage 2 integration, bundle format compatibility, and backward compatibility requirements
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md)

## Bundle Format Compatibility

- [ ] CHK001 — Are all required [ARCH_HEADER] fields for PHP bundles explicitly listed with format and examples? [Completeness, Spec §FR-004]
- [ ] CHK002 — Is the relationship between LANGUAGE field in ARCH_HEADER and Extension Mapper routing clearly defined? [Clarity, Gap]
- [ ] CHK003 — Are the new fields (LANGUAGE, PLATFORM, IMPLICIT_DEPS) specified as required or optional? [Clarity, Spec §FR-004]
- [ ] CHK004 — Is the fragment delimiter format (`--- FRAGMENT: <name> (<type>) ---`) distinguished from Python's bundle delimiter (`--- BUNDLE ---`)? [Consistency, Contract §bundle-format]
- [ ] CHK005 — Is the `[LEGACY_SIGNATURES]` section separator (`---` between entries) unambiguous against fragment delimiters? [Ambiguity, Contract §bundle-format]

## parse_bundle() Changes

- [ ] CHK006 — Is the generic section parser regex (`\[(\w+)\]` or `\[([A-Z_]+)\]`) formally specified? [Clarity, Spec §FR-004]
- [ ] CHK007 — Are requirements defined for what happens when a new section name collides with existing ones (ARCH_HEADER, MODULE_MAP, GOVERNANCE_HEADER)? [Edge Case, Spec §FR-004]
- [ ] CHK008 — Is the `extra_` prefix convention for captured unknown sections documented as a stable contract? [Clarity, Gap]
- [ ] CHK009 — Is backward compatibility explicitly required: existing Python bundles must parse identically after changes? [Consistency, Spec §FR-004]

## get_v2_fragments() Changes

- [ ] CHK010 — Are requirements defined for how [LEGACY_SIGNATURES] content is injected into Teacher prompts? [Completeness, Spec §FR-005]
- [ ] CHK011 — Is the injection point in `build_system_with_blueprint()` vs `_prompt()` explicitly specified? [Clarity, Spec §FR-005]
- [ ] CHK012 — Are requirements defined for what happens when a PHP bundle has no [LEGACY_SIGNATURES] section? [Edge Case, Gap]
- [ ] CHK013 — Is the FUNCTIONAL_UNIT routing behavior specified when Extension Mapper has no entry for the file extension? [Edge Case, Spec §FR-015]

## Backward Compatibility

- [ ] CHK014 — Are regression requirements defined to ensure existing Python bundles continue processing unchanged? [Completeness, Spec §FR-004]
- [ ] CHK015 — Is the interaction between new generic section parser and existing hardcoded section handling (MODULE_MAP, GOVERNANCE_HEADER) explicitly defined? [Consistency, Gap]
- [ ] CHK016 — Are requirements defined for mixed-language repositories (both .py and .php files)? [Coverage, Gap]
- [ ] CHK017 — Is the fallback behavior specified when `profile` is not `php_legacy` but `.php` files are encountered? [Edge Case, Gap]

## Stage 2 → Teacher Roundtrip

- [ ] CHK018 — Are requirements defined for validating that Teacher output conforms to the 3-section schema? [Completeness, Spec §SC-009]
- [ ] CHK019 — Is the Teacher output parsing strategy specified (regex, section discovery, or dedicated parser)? [Clarity, Gap]
- [ ] CHK020 — Are requirements defined for partial Teacher output (only 1 or 2 of 3 sections returned)? [Edge Case, Gap]

## Notes

- FR-004 specifies both what the driver must produce AND what Stage 2 must be modified to consume — requirements span two systems
- Contract bundle-format.md provides concrete format examples but spec does not reference it normatively
