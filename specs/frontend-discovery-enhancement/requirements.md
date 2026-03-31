# Requirements: Frontend Discovery Enhancement

## Goal
Verify that the data factory processes all fragment types (1-5) correctly across Python, TypeScript, PHP, and YAML repositories with per-file adapter selection, enabling dataset generation with architecture context.

## User Stories

### US-1: Generate Type 1 (FUNCTIONAL_UNIT) for Python code with tests
**As a** dataset builder
**I want to** pair Python logic files with their test files
**So that** training samples include both implementation and verification for code generation

**Acceptance Criteria:**
- [ ] AC-1.1: Files under `MIN_SIZE` chars are emitted if test exists (size gate bypass)
- [ ] AC-1.2: Test file located by exact name mirror (e.g., `module.py` → `test_module.py`)
- [ ] AC-1.3: Output bundle includes `[ARCH_HEADER]` with dependencies from Python AST parser
- [ ] AC-1.4: Bundle format: `=== LOGICAL ENTITY: {id} ===`, `Type: FUNCTIONAL_UNIT`, logic file, test file

### US-2: Generate Type 3 (LOGIC_ONLY) for Python code without tests
**As a** dataset builder
**I want to** emit long standalone logic files as training samples
**So that** substantial code modules are available even without explicit tests

**Acceptance Criteria:**
- [ ] AC-2.1: Files ≥ `LOGIC_ONLY_MIN_CHARS` (1000) chars are emitted
- [ ] AC-2.2: Files < `MIN_SIZE` (200 chars) are skipped
- [ ] AC-2.3: Python-only files pass `GOLD_PATTERNS` filter if no test exists
- [ ] AC-2.4: Output bundle: `Type: LOGIC_ONLY`, single file content

### US-3: Generate Type 4 (MODULE_BLUEPRINT) for all repository types
**As a** dataset builder
**I want to** aggregate architecture context (anchor files, manifest, README) into one bundle
**So that** code generation models understand module structure and dependencies

**Acceptance Criteria:**
- [ ] AC-3.1: Always emitted for each discovered module (no size filter)
- [ ] AC-3.2: Includes `[MODULE_MAP]` with module name, anchor type, file list
- [ ] AC-3.3: Includes `[DEPENDENCIES]` from manifest.json if present (dependencies, requirements)
- [ ] AC-3.4: Includes `[SCHEMA]` from services.yaml if present
- [ ] AC-3.5: Includes `[VOCABULARY]` from const.py if present
- [ ] AC-3.6: Includes `[README]` section if README.md exists or is inherited
- [ ] AC-3.7: Works for Python (manifest/__init__.py), TypeScript (directory scan), YAML (yaml strategy), PHP (filesystem)

### US-4: Generate Type 5 (GOVERNANCE_RULES) from repo-level rules
**As a** dataset builder
**I want to** extract coding standards and guidelines from `.codecov.yml`, `.gitlab-ci.yml`, `mypy.ini`
**So that** generated code follows repository conventions

**Acceptance Criteria:**
- [ ] AC-4.1: Governance files detected at repository root (not in modules)
- [ ] AC-4.2: Output bundle includes `[GOVERNANCE_HEADER]` with repo prefix
- [ ] AC-4.3: Full file content emitted in `[RULES]` section
- [ ] AC-4.4: Emitted before module processing begins

### US-5: Process TypeScript files with TypeScriptAdapter
**As a** dataset builder
**I want to** parse `.ts` and `.tsx` files for dependencies and structure
**So that** Frontend/Lit components are correctly extracted with import dependencies

**Acceptance Criteria:**
- [ ] AC-5.1: `.ts` and `.tsx` files route to `TypeScriptAdapter.parse_file()`
- [ ] AC-5.2: Extracts imports from `import` statements (both named and default)
- [ ] AC-5.3: Extracts `@customElement` decorator tag names for Lit components
- [ ] AC-5.4: Extracts `@property` decorator attributes (type, reflect, state)
- [ ] AC-5.5: Dependencies list includes relative and absolute imports

### US-6: Process YAML/Jinja files with YamlAdapter
**As a** dataset builder
**I want to** parse `.yaml`, `.yml`, `.jinja`, `.jinja2` files for structure and dependencies
**So that** Home Assistant integrations and configurations are extracted correctly

**Acceptance Criteria:**
- [ ] AC-6.1: `.yaml`, `.yml`, `.jinja`, `.jinja2` files route to `YamlAdapter.parse_file()`
- [ ] AC-6.2: Extracts service definitions from YAML structure
- [ ] AC-6.3: Extracts Jinja templates and their variables
- [ ] AC-6.4: YAML anchor references (`&`, `*`) are preserved

### US-7: Process PHP files with PhpLegacyAdapter
**As a** dataset builder
**I want to** parse `.php` files for classes and functions
**So that** PHP legacy code is included in training data

**Acceptance Criteria:**
- [ ] AC-7.1: `.php` files route to `PhpLegacyAdapter.parse_file()`
- [ ] AC-7.2: Extracts class definitions and method signatures
- [ ] AC-7.3: Extracts function definitions (non-class methods)
- [ ] AC-7.4: Dependencies list includes `require`/`include` statements

### US-8: Process files by extension regardless of repository profile
**As a** dataset builder
**I want to** use the correct adapter based on file extension, not repository type
**So that** mixed-repository repositories (Python with JS config) process correctly

**Acceptance Criteria:**
- [ ] AC-8.1: `.py` files always use `PythonAstAdapter`
- [ ] AC-8.2: `.ts`/`.tsx` files always use `TypeScriptAdapter`
- [ ] AC-8.3: `.php` files always use `PhpLegacyAdapter`
- [ ] AC-8.4: `.yaml`/`.yml`/`.jinja` files always use `YamlAdapter`
- [ ] AC-8.5: Adapter selection happens per-file, not per-repo

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Type 1 FUNCTIONAL_UNIT generation | High | Logic + test pair emitted, size gate bypass, `[ARCH_HEADER]` with dependencies |
| FR-2 | Type 3 LOGIC_ONLY generation | High | Size-gated standalone files, GOLD_PATTERNS filter for Python, `[ARCH_HEADER]` |
| FR-3 | Type 4 MODULE_BLUEPRINT generation | High | Always emitted per module, `[MODULE_MAP]`, `[DEPENDENCIES]`, `[SCHEMA]`, `[VOCABULARY]`, `[README]` |
| FR-4 | Type 5 GOVERNANCE_RULES generation | Medium | Repo-level files extracted, `[GOVERNANCE_HEADER]`, `[RULES]` section |
| FR-5 | Per-file adapter selection | High | Adapter selected from file suffix: `.ts` → TypeScriptAdapter, `.py` → PythonAstAdapter, `.php` → PhpLegacyAdapter, `.yaml` → YamlAdapter |
| FR-6 | Discovery strategy per repository type | High | manifest (HA integrations), init (Python packages), typescript (`.ts`), yaml (`.yaml/.jinja`), filesystem (PHP) |
| FR-7 | README inheritance | Medium | If module lacks README, walk up to repository root and inherit |
| FR-8 | Test file detection | High | Mirror-based detection: `module.py` → `test_module.py` or `tests/test_module.py` |
| FR-9 | Parse error handling | High | Configurable policies: `abort`, `skip`, `mark_and_continue`, `fallback` with metrics tracking |
| FR-10 | Size gate configuration | Medium | `MIN_SIZE` (200 chars) for general filtering, `LOGIC_ONLY_MIN_CHARS` (1000) for standalone, `MAX_SIZE_BACKEND`/`MAX_SIZE_FRONTEND` caps |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Adapter extensibility | Time to add new language | < 1 hour (register in factory.py, implement ExtractorAdapter protocol) |
| NFR-2 | Memory efficiency | Files in memory | < 1000 concurrent files processed |
| NFR-3 | Error recovery | Parse error handling | Never crash on malformed files (policy-based handling) |
| NFR-4 | Processing throughput | Files per second | ≥ 50 files/sec on reference hardware (AMD Threadripper) |
| NFR-5 | Config flexibility | Profile vs extensions | Accept both for backward compatibility |

## Glossary

- **Adapter**: Language-specific parser implementing `ExtractorAdapter` protocol (e.g., `PythonAstAdapter`, `TypeScriptAdapter`)
- **Anchor File**: Module-defining file (manifest.json, const.py, services.yaml, __init__.py, strings.json)
- **Blueprint**: Architecture context bundle for a module, aggregated from anchor files
- **Discovery Strategy**: Algorithm for finding modules (manifest, init, typescript, yaml, filesystem, directory_scan)
- **Fragment**: Extracted code unit from repository
- **Fragment Type**: Classification of fragment (1=FUNCTIONAL_UNIT, 2=NOT_IMPLEMENTED, 3=LOGIC_ONLY, 4=MODULE_BLUEPRINT, 5=GOVERNANCE_RULES)
- **GOLD_PATTERNS**: List of strings indicating substantial code (`def`, `class`, `async def`, etc.)
- **Logic File**: Non-test, non-anchor file containing code to process
- **Module**: Logical grouping of files discovered via strategy (package, component, feature)
- **Test File**: File containing tests for logic file (mirror naming or tests/ directory)

## Out of Scope

- Type 2 (FUNCTIONAL_UNIT_WITH_CONTEXT) - intentionally removed, README content folded into MODULE_BLUEPRINT
- Repository-level adapter selection (always per-file based on extension)
- Filtering files by discovery strategy (all files with adapters are processed)
- Custom adapter implementation (registering existing adapters only)
- Multi-language adapter selection for single file (one adapter per file)

## Dependencies

- **Adapter Protocol**: `src/utils/extractors/base.py` defines `ExtractorAdapter` interface
- **Factory Registry**: `src/utils/extractors/factory.py` maps extensions to adapter classes
- **Config Schema**: `ProcessingConfig` in `src/discovery/metadata_enricher.py` with `extensions`, `profile_extensions` support
- **Discovery Config**: `src/discovery/file_scanner.py` with module discovery strategies
- **Size Thresholds**: `src/discovery/file_scanner.py` constants (`MIN_SIZE`, `LOGIC_ONLY_MIN_CHARS`, etc.)

## Success Criteria

- All 4 implemented fragment types (1, 3, 4, 5) generate correctly for Python, TypeScript, PHP, and YAML repositories
- Per-file adapter selection processes all file types regardless of repository profile
- MODULE_BLUEPRINT generation works across all discovery strategies (manifest, init, typescript, yaml, filesystem)
- Test file detection successfully pairs logic files for Type 1 generation
- Parse error handling prevents repository-wide failures with configurable policies

## Unresolved Questions

1. **Type 2 removal**: CONFIRMED - Type 2 (FUNCTIONAL_UNIT_WITH_CONTEXT) is intentionally not implemented; README content folded into MODULE_BLUEPRINT
2. **Adapter selection granularity**: CONFIRMED in Phase 7 fix - adapter selection is per-file based on extension, not per-repo based on profile
3. **Discovery strategy vs file filtering**: Discovery strategy determines architecture context only, does NOT filter files - all files with adapters are processed
4. **Type 4 for TypeScript/PHP**: MODULE_BLUEPRINT works for all discovery strategies - TypeScript uses directory scan, PHP uses filesystem, both aggregate anchor files correctly
5. **Adapter per-file processing**: CONFIRMED - `metadata_enricher.py` line 495-496 shows `adapter = get_adapter(mf.path.suffix)` then `adapter.parse_file(mf.path)` for each file

## Next Steps

1. Confirm Type 2 intentional removal in code comments/docs
2. Verify per-file adapter selection fix (Phase 7) is merged and tested
3. Run integration test on mixed-language repository (Python + TypeScript config files)
4. Validate MODULE_BLUEPRINT generation for TypeScript and PHP repos
5. Document adapter extension pattern for future languages
6. Add Type 1-5 fragment type constants to codebase documentation

