# Data Model & Entity Requirements Quality Checklist: PHPLegacyDriver

**Purpose**: Validate completeness, consistency, and clarity of entity definitions, invariants, and validation rules
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md), [data-model.md](../data-model.md)

## Entity Definition Completeness

- [ ] CHK001 — Are all 5 entities (PhpFragment, LegacySignature, IncludeGraph, PlatformProfile, ImplicitDependency) consistently defined across spec and data-model? [Completeness, Spec §Key Entities]
- [ ] CHK002 — Is the relationship between spec's Key Entities section and data-model.md's Entity Definitions aligned in field names? [Consistency, Gap]
- [ ] CHK003 — Are entity constructors/factories specified, or are bare dataclass constructors assumed sufficient? [Clarity, Gap]
- [ ] CHK004 — Is the serialization format for entities specified (JSON, JSONL, or only in-memory)? [Gap]

## Category Taxonomy Consistency

- [x] CHK005 — Are the 6 semantic categories in spec FR-003 (PERSISTENCE, STATE, MODULE_LINK, SECURITY_SMELL, CONSTANT_DEF, MODERN_REFERENCE) consistent with data-model's `semantic_label` enum (DB_ACCESS, ROUTING, AUTH_SESSION, OUTPUT_RENDER, FILE_IO, BUSINESS_LOGIC)? **RESOLVED: Two separate taxonomies defined. LEGACY_ACTION = business intent of fragment (PhpFragment.legacy_action). SIGNATURE_TYPE = technical debt pattern (LegacySignature.signature_type). Not mixed.** [Conflict → Resolved, data-model.md §Taxonomy]
- [x] CHK006 — Is the `category` field in LegacySignature using the same enum as PhpFragment's `semantic_label`? **RESOLVED: Field renamed to `signature_type` in LegacySignature. Uses SIGNATURE_TYPE enum. PhpFragment uses `legacy_action` with LEGACY_ACTION enum. Intentionally different.** [Consistency → Resolved]
- [x] CHK007 — Are there TWO different category taxonomies (one for signatures, one for fragments) or should they be unified? **RESOLVED: Two taxonomies by design — LEGACY_ACTION (what code does) vs SIGNATURE_TYPE (what’s wrong). Unifying them would confuse the model between business intent and debt classification.** [Ambiguity → Resolved]
- [x] CHK008 — Is the mapping between the two taxonomies (e.g., PERSISTENCE ↔ DB_ACCESS) documented? **RESOLVED: Not a 1:1 mapping by design. A single fragment with LEGACY_ACTION=DB_ACCESS can carry signatures of SIGNATURE_TYPE=PERSISTENCE AND SECURITY_SMELL simultaneously. See data-model.md §Taxonomy example.** [Gap → Resolved]

## Invariant Completeness

- [ ] CHK009 — Are invariants for `PhpFragment.raw_content` (non-empty, at least one PHP token) validateable at construction time? [Measurability, data-model §PhpFragment]
- [x] CHK010 — Is the `PlatformProfile.signature_patterns` dict[str, str] type correct given it breaks immutability of a frozen dataclass? **RESOLVED (v3): Uses `dict[str, str]` as the declared field type for ergonomic construction, then `__post_init__` calls `object.__setattr__(self, 'signature_patterns', MappingProxyType(self.signature_patterns))` to coerce to an immutable `MappingProxyType` at runtime. Raises `TypeError` on mutation. Pickle-safe for ProcessPoolExecutor. Bypasses frozen-dataclass restriction cleanly without tuple hacks.** [Consistency → Resolved, data-model.md §PlatformProfile]
- [ ] CHK011 — Are validation rules defined for `IncludeEdge.target_file` path normalization ("no `..` traversal outside repo")? [Completeness, data-model §IncludeGraph]
- [ ] CHK012 — Is `ImplicitDependency.confidence` (0.0-1.0) heuristic calculation documented with factors that affect it? [Clarity, data-model §ImplicitDependency]

## Relationship Clarity

- [ ] CHK013 — Is the 1:N relationship between PhpFragment and LegacySignature contractually defined (ownership, lifecycle)? [Clarity, data-model §Relationships]
- [ ] CHK014 — Is the relationship between ImplicitDependency and IncludeGraph (implicit vs explicit dependencies) clearly distinguished? [Clarity, Gap]
- [x] CHK015 — Are requirements defined for PhpFragment referencing preamble content (virtual attachment mentioned in FR-018)? **RESOLVED: Virtual Reference / SHA-256 Hash pattern. PhpFragment.preamble_ref stores the 64-char SHA-256 hex digest of the bootstrap fragment's `raw_content`. Stage 2 resolves it by matching hash in blueprint cache and injects via ${preamble}. TokenCounter prevents oversized preamble injection (threshold: 800 tokens; Summarization Step if exceeded). Bootstrap fragments themselves have preamble_ref=None.** [Gap → Resolved, research.md §R-011, data-model.md §PhpFragment]

## State Transition Coverage

- [ ] CHK016 — Is the Fragment Lifecycle (raw → fragmented → labeled → enriched → bundled) complete with error states? [Coverage, data-model §State Transitions]
- [ ] CHK017 — Is the Platform Detection Flow defined with failure/fallback transitions? [Coverage, data-model §State Transitions]
- [ ] CHK018 — Are requirements defined for re-processing (idempotency of fragment extraction)? [Gap]

## Notes

- ~~CRITICAL: Spec FR-003 and data-model.md use DIFFERENT category taxonomies~~ — RESOLVED: CHK005-CHK008 resolved with dual taxonomy design (LEGACY_ACTION vs SIGNATURE_CATEGORY with explicit `_SMELL`/`_POLLUTION`/`_VULN` suffixes)
- ~~PlatformProfile's `signature_patterns: dict[str, str]`~~ — RESOLVED (v3): Now uses `dict` declaration + `MappingProxyType` coercion in `__post_init__` via `object.__setattr__`
- ~~preamble_ref as fragment_id string~~ — RESOLVED: Now SHA-256 hex digest (64 chars) of bootstrap fragment's `raw_content`
- ImplicitDependency is defined in data-model but not referenced in bundle-format contract — unclear how it’s serialized [still open]
- DIRTY fragment type added to PhpFragment — see data-model.md for fail-safe behavior
- FastBraceScanner documented in research.md R-003 as the implementation decision for brace-matching
