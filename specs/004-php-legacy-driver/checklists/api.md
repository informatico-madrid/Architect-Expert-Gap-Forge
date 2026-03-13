# API & Interface Requirements Quality Checklist: PHPLegacyDriver

**Purpose**: Validate completeness and clarity of adapter protocol, factory registration, and Extension Mapper interface requirements
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md)

## ExtractorAdapter Protocol Compliance

- [ ] CHK001 — Are the exact Protocol methods (`parse_file`, `extract_dependencies`) documented with their expected behavior for PHP input? [Completeness, Spec §FR-001]
- [ ] CHK002 — Is the return value of `parse_file()` specified when `ast_tree` is `None` (PHP has no AST)? [Clarity, Spec §FR-001]
- [ ] CHK003 — Is the `ParseResult.dependencies` population strategy from regex matches explicitly defined? [Clarity, Gap]
- [ ] CHK004 — Are error handling requirements for `parse_file()` consistent with `ParseError` dataclass usage? [Consistency, Spec §FR-001]
- [ ] CHK005 — Is the adapter registration profile name `php_legacy` documented as a stable contract or internal detail? [Clarity, Spec §FR-001]

## Extension Mapper Contract

- [ ] CHK006 — Is the Extension Mapper dict (`_EXTENSION_FRAGMENTERS`) interface specified with exact signature `Callable[[str, str], list[dict]]`? [Completeness, Spec §FR-015]
- [ ] CHK007 — Are requirements defined for what happens when an unknown file extension is encountered by the Extension Mapper? [Edge Case, Spec §FR-015]
- [ ] CHK008 — Is backward compatibility explicitly required: `.py` must continue routing to `_ast_fragment_list()`? [Consistency, Spec §FR-015]
- [ ] CHK009 — Are requirements defined for registering new extensions at runtime vs. compile-time? [Clarity, Gap]
- [ ] CHK010 — Is the Extension Mapper's relationship to `allowed_extensions` filter in `get_v2_fragments()` documented? [Consistency, Gap]

## Factory Registration

- [ ] CHK011 — Is the registration mechanism in `_ADAPTER_REGISTRY` specified (lazy-load path string vs. class reference)? [Completeness, Gap]
- [ ] CHK012 — Are requirements defined for what happens when `get_adapter("php_legacy")` is called but the adapter module is missing? [Edge Case, Gap]
- [ ] CHK013 — Is the caching behavior of `get_adapter()` documented for PHP adapter instances? [Clarity, Gap]

## Module Discovery Strategy

- [ ] CHK014 — Is the new `directory_scan` strategy formally defined with its file matching rules? [Completeness, Spec §FR-001]
- [ ] CHK015 — Are exclude patterns for `directory_scan` (`vendor/`, `node_modules/`, `tests/`, `cache/`) specified as configurable or hardcoded? [Clarity, Gap]
- [ ] CHK016 — Is `directory_scan` interaction with existing strategies (manifest, init, directory, manual_mapping) defined? [Consistency, Gap]
- [ ] CHK017 — Are requirements defined for ProcessingConfig validation when `profile="php_legacy"` and `extensions` contain non-PHP extensions? [Edge Case, Gap]

## Notes

- Research R-001 and R-002 provide more interface detail than spec FR-001 — consider promoting key decisions to spec level
- Extension Mapper (FR-015) is the most architecturally impactful interface change — forward compatibility deserves explicit requirements
