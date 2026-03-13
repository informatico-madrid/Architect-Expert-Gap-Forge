# Multi-Platform Requirements Quality Checklist: PHPLegacyDriver

**Purpose**: Validate completeness and clarity of platform detection, profile management, and multi-platform support requirements
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md)

## Platform Detection

- [ ] CHK001 — Are marker files for all 8 platforms explicitly listed with expected paths? [Completeness, Spec §FR-010]
- [ ] CHK002 — Is the detection algorithm specified: priority order, scoring mechanism, or first-match? [Clarity, Spec §FR-010]
- [ ] CHK003 — Are requirements defined for repositories that match markers of multiple platforms simultaneously? [Edge Case, Spec §FR-010]
- [ ] CHK004 — Is the `generic_php` fallback explicitly required when no platform markers are found? [Completeness, Spec §FR-009]
- [ ] CHK005 — Are detection requirements defined for versioned platforms (osCommerce 2.x vs 4.x, PrestaShop 1.6 vs 1.7)? [Coverage, Gap]
- [ ] CHK006 — Is the detection granularity specified: per-repository or per-directory? [Ambiguity, Gap]

## Platform Profiles

-- [ ] CHK007 — Are the canonical platform profiles consistent across spec and plan: `oscommerce`, `oscommerce_phoenix`, `wordpress`, `zencart`, `openmage`, `prestashop`, `codeigniter`, `suitecrm`? [Consistency, Spec §FR-009]
- [ ] CHK008 — Is OpenMage listed in spec SC-007 but called Magento in FR-009 — are they the same profile? [Ambiguity, Spec §FR-009, §SC-007]
- [ ] CHK009 — Are PrestaShop and PrestaShopCorp (two directories in multi_legacy/) covered by one profile or two? [Ambiguity, Gap]
- [ ] CHK010 — Is the relationship between `gburton` directory in multi_legacy/ and a named platform profile defined? [Gap]
- [ ] CHK011 — Are exclude directories specified per platform (e.g., WordPress `wp-content/plugins/` vs `wp-admin/`)? [Coverage, Gap]

## Anti-Patterns Mapping Snippets

- [ ] CHK012 — Are anti-pattern mapping requirements defined for all 8 snippet files listed in the plan? [Completeness, Spec §FR-024]
- [ ] CHK013 — Is the snippet format (ANTI → MODERN → MAPPING per pattern) consistently specified across all categories in FR-024? [Consistency, Spec §FR-024]
- [ ] CHK014 — Are the 4 anti-pattern categories (persistence, global state, modularity, security) required for every platform snippet? [Completeness, Spec §FR-024]
- [ ] CHK015 — Is the snippet injection mechanism (into Teacher prompt via `${governance}`) explicitly documented? [Clarity, Gap]
- [ ] CHK016 — Are requirements defined for snippet maintenance when new platform patterns are discovered? [Gap]

## Legacy Puro vs Modernizado Detection

- [ ] CHK017 — Are the criteria for classifying code as "Legacy Puro" vs "Legacy Modernizado" vs "Hybrid" measurable? [Measurability, Spec §FR-016]
- [ ] CHK018 — Is the threshold for "hybrid" classification specified (e.g., % of OOP vs procedural code)? [Clarity, Spec §FR-016]
- [ ] CHK019 — Is MODERN_REFERENCE category (FR-003) clearly defined with specific patterns (namespaces, `use`, PSR-4)? [Clarity, Spec §FR-003]
- [ ] CHK020 — Are requirements consistent between FR-016 (Legacy Puro/Modernizado/Hybrid) and LegacySignature's style classification field? [Consistency, Spec §FR-016]

## Notes

- SC-007 lists 8 specific repositories (osCommerce, osCommerce Phoenix/gburton, WordPress, ZenCart, OpenMage, PrestaShop, CodeIgniter, SalesAgility/SuiteCRM) — FR-009 profile names now aligned: `openmage` (not Magento), `suitecrm` (maps to salesagility dir)
- Plan.md lists `gburton` in multi_legacy/ directories but no profile matches this name
- PrestaShop appears twice in multi_legacy/ (PrestaShop + PrestaShopCorp) — spec doesn't address this
