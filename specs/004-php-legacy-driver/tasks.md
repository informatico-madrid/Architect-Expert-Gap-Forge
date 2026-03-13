# Tasks: PHPLegacyDriver (Regex-Based Extractor)

**Feature Branch**: `004-php-legacy-driver`
**Generated**: 2026-03-13 (post spec-003 refactor reconciliation)
**Input**: [spec.md](spec.md) · [plan.md](plan.md) · [data-model.md](data-model.md) · [research.md](research.md) · [contracts/bundle-format.md](contracts/bundle-format.md) · [contracts/prompt-schema.md](contracts/prompt-schema.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable — targets a different file or independent concern from concurrent tasks
- **[US#]**: User story label (maps to spec.md User Story N)
- All file paths are relative to repository root

---

## Phase 1: Setup

**Purpose**: Create PHP test fixtures and add pytest infrastructure so every phase can run against representative data from day one.

- [ ] T001 Create `tests/fixtures/php_legacy/` directory and add fixture loader + `php_legacy` pytest marks in `tests/conftest.py`
- [ ] T002 [P] Create `tests/fixtures/php_legacy/oscommerce_categories.php` — representative osCommerce 2.3 file (≥150 lines, mixed PHP/HTML, `tep_db_query`, `global $languages_id`, `include`, `$_SESSION`, `switch/case` blocks with `LEGACY_ACTION` names)
- [ ] T003 [P] Create `tests/fixtures/php_legacy/wordpress_ajax_actions.php` — representative WordPress file (`$wpdb->prepare`, `$wpdb->get_results`, `wp_send_json_error`, `add_action`, `global $wpdb`)
- [ ] T004 [P] Create `tests/fixtures/php_legacy/zencart_customers.php` — representative ZenCart file (`zen_db_perform`, `$_SESSION['customer_id']`, `zen_redirect`, `require DIR_WS_CLASSES . 'order.php'`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core entity dataclasses and low-level utilities used by every user story. No user story implementation can begin until Phase 2 is complete.

**⚠️ CRITICAL**: Complete all T005–T012 before Phase 3.

- [ ] T005 Define `PhpFragment` + `ImplicitDependency` typed frozen dataclasses using `@dataclass(frozen=True, slots=True)` in `src/discovery/php_fragmenter.py` — required fields: `name`, `fragment_type` (enum set: function|class|switch_block|bootstrap|mixed_html|catchall), `source_file: Path`, `start_line: int`, `end_line: int`, `raw_content: str`, `legacy_action: str` (LEGACY_ACTION enum), `preamble_ref: str | None` (SHA-256 hex or None for bootstrap fragments), `dependencies: tuple[str, ...]`, `platform_hints: tuple[str, ...]`; default fields: `file_style: str = "LEGACY_PURE"`, `implicit_deps: tuple[ImplicitDependency, ...] = ()`, `signatures: tuple[LegacySignature, ...] = ()`. `ImplicitDependency` fields: `target_symbol: str`, `dependency_type: str` (global_var|constant|function_call|class_instantiation), `confidence: float` (0.0–1.0)
- [ ] T006 [P] Define `LegacySignature` typed frozen dataclass using `@dataclass(frozen=True, slots=True)` in `src/discovery/php_signatures.py` — fields: `pattern_name: str`, `category: str` (SIGNATURE_CATEGORY enum set), `matched_text: str`, `line_number: int`, `severity: str` (critical|warning|info), `modern_equivalent: str`
- [ ] T007 [P] Define `IncludeGraph` + `IncludeEdge` typed frozen dataclasses using `@dataclass(frozen=True, slots=True)` in `src/discovery/php_include_graph.py` — IncludeEdge: `source_file`, `target_file`, `include_type`, `line_number`; IncludeGraph: `edges: tuple[IncludeEdge, ...]`, `entry_points: tuple[str, ...]`, methods `neighbors()` and `reverse_neighbors()`
- [ ] T008 [P] Define `PlatformProfile` typed frozen dataclass using `@dataclass(frozen=True, slots=True)` with `MappingProxyType` coercion in `__post_init__` via `object.__setattr__` in `src/discovery/php_platform_profiles.py` — fields: `name: str`, `marker_files: tuple[str, ...]`, `marker_patterns: tuple[str, ...]`, `exclude_dirs: tuple[str, ...]`, `snippet_path: str`, `signature_patterns: dict[str, str]` → coerced to `MappingProxyType` at runtime
- [ ] T009 Implement `strip_html_markup(source: str) -> str` — extracts only `<?php ... ?>` blocks from mixed PHP/HTML/JS files in `src/discovery/php_fragmenter.py`
- [ ] T010 [P] Implement `fast_brace_scan(source: str, open_pos: int) -> int` — character-loop brace matcher returning close position or `-1` on unmatched brace in `src/discovery/php_fragmenter.py`; callers abort fragment on `-1`: log `{source_file, name, start_line, reason}` to `needs_manual_review.json` and skip the fragment entirely
- [ ] T011 [P] Implement `read_php_file(path: Path) -> str` — reads file with UTF-8 fallback to latin-1; logs warning on fallback; raises `PhpReadError` if both fail in `src/discovery/php_fragmenter.py`
- [ ] T012 Write unit tests covering `strip_html_markup`, `fast_brace_scan` (matched, unmatched, nested), and `read_php_file` (utf8, latin1, binary) in `tests/unit/test_php_fragmenter.py`

**Checkpoint**: Core types and low-level utilities are ready. User story phases can now begin.

---

## Phase 3: User Story 1 — Extracción de fragmentos PHP legacy (Priority: P1) 🎯 MVP

**Goal**: `PhpLegacyAdapter` processes a PHP repository → emits `.txt` bundles with valid `[ARCH_HEADER]` parseable by Stage 2 (`parse_bundle()` in `src/factory/fragment_extractor.py`), fragmented by heuristic blocks (functions, switch/case, Preamble Rule), via 3-stage parallel pipeline (ThreadPool IO → ProcessPool CPU → ThreadPool writes).

**Covers**: FR-001, FR-002, FR-008, FR-011, FR-012, FR-013, FR-015, FR-016, FR-017, FR-018, FR-019

**Independent Test**: Run `PhpLegacyAdapter` on osCommerce fixture → assert ≥1 `.txt` emitted; assert `parse_bundle()` (from `src/factory/fragment_extractor.py`) returns non-empty dict with `MODULE` and `FRAGMENT_TYPE` fields.

- [ ] T013 [P] [US1] Write unit tests for `_extract_function_blocks`, `_extract_preamble`, `_extract_switch_cases`, `_fragment_by_size` in `tests/unit/test_php_fragmenter.py`
- [ ] T014 [P] [US1] Write unit tests for `PhpLegacyAdapter` constructor, `parse_file()` signature (returns `ParseResult` from `src/utils/extractors/base.py`), and `extract_dependencies()` shape in `tests/unit/test_php_legacy_adapter.py`
- [ ] T015 [US1] Implement `_extract_preamble(source: str) -> tuple[str, str]` — returns `(preamble_content, remaining_source)`; computes `hashlib.sha256(preamble_content.encode()).hexdigest()` for `preamble_ref` in `src/discovery/php_fragmenter.py`
- [ ] T016 [US1] Implement `_extract_function_blocks(source: str, source_file: Path) -> list[tuple[int, int, str]]` — regex detection `function\s+\w+\s*\(`; uses `fast_brace_scan` for closing brace; on `-1` abort: log to `needs_manual_review.json`, skip the fragment in `src/discovery/php_fragmenter.py`
- [ ] T017 [US1] Implement `_extract_switch_cases(source: str, source_file: Path) -> list[tuple[int, int, str, str]]` — returns `(start, end, raw, case_label)`; sub-chunks cases >500 lines preserving case header; on `fast_brace_scan` failure abort entire switch block, log to `needs_manual_review.json` in `src/discovery/php_fragmenter.py`
- [ ] T018 [US1] Implement `_fragment_by_size(source: str, max_lines: int, overlap: int = 20) -> list[tuple[int, int, str]]` — size-based fallback with context overlap for files with no function/case delimiters in `src/discovery/php_fragmenter.py`
- [ ] T019 [US1] Implement `_classify_file_style(source: str) -> str` — returns `"LEGACY_PURE"` | `"LEGACY_MODERNIZED"` | `"HYBRID"` per Golden Rule (R-007) in `src/discovery/php_fragmenter.py`
- [ ] T020 [US1] Implement top-level `process_php_file(path: Path, content: str, profile_name: str) -> list[PhpFragment]` in `src/discovery/php_fragmenter.py` — must be module-level function (not lambda/closure) for `ProcessPoolExecutor` pickle compatibility; orchestrates preamble extraction, function/switch/fallback fragmentation, file_style classification
- [ ] T021 [US1] Implement `format_arch_header(fragment: PhpFragment) -> str` — produces all required fields (MODULE, REPO_PREFIX, FILE_ROLE, FRAGMENT_TYPE, LANGUAGE, PLATFORM, LOCAL_IMPORTS, DEPENDENCIES, NEIGHBORS, IMPLICIT_DEPS, LEGACY_ACTION, PREAMBLE_REF) per bundle-format contract in `src/discovery/php_fragmenter.py`
- [ ] T022 [US1] Implement `write_bundle(fragment: PhpFragment, output_dir: Path) -> Path` — writes `[ARCH_HEADER]\n{header}\n--- FILE: {fragment_name} ({fragment_type}) ---\n{raw_content}` to `.txt` file in `src/discovery/php_fragmenter.py`; uses the same `--- FILE:` delimiter as Stage 2’s `parse_bundle()` for direct compatibility; only structurally valid fragments reach this function (malformed ones aborted at extraction)
- [ ] T023 [US1] Implement `PhpLegacyAdapter` class in `src/utils/extractors/php_legacy_adapter.py` — implements `ExtractorAdapter` protocol from `src/utils/extractors/base.py`; wraps 3-stage pipeline: `ThreadPoolExecutor(max_workers=32)` for IO reads → `ProcessPoolExecutor(os.cpu_count(), chunksize=50)` for CPU fragmentation → `ThreadPoolExecutor(max_workers=16)` for writes; exposes `parse_file(path) -> ParseResult` and `extract_dependencies(path) -> list[Dependency]`
- [ ] T024 [US1] Register `PhpLegacyAdapter` in `_ADAPTER_REGISTRY` dict in `src/utils/extractors/factory.py` under key `"php_legacy"` with value `"src.utils.extractors.php_legacy_adapter.PhpLegacyAdapter"`
- [ ] T025 [US1] Add `_EXTENSION_FRAGMENTERS: dict[str, Callable]` Extension Mapper to `src/factory/fragment_extractor.py` — map `{".py": _ast_fragment_list, ".php": _php_fragment_list}`; update `get_v2_fragments()` to dispatch via `_EXTENSION_FRAGMENTERS.get(suffix)` lookup instead of hardcoded `_ast_fragment_list()` call; implement `_php_fragment_list(logic_fname: str, logic_code: str, context_str: str, extra_fields: dict) -> list[FragmentTypedDict]`: PHP bundles arrive pre-divided (fragmentation done in Phase 3), so return exactly `[{**extra_fields, "name": Path(logic_fname).stem, "skeleton": logic_code, "original": logic_code, "context": context_str}]` — one element per `--- FILE:` chunk, no AST re-parsing; `legacy_signatures` and `implicit_deps` arrive pre-populated in `extra_fields` (via T035/T039); the returned dict **must** satisfy `FragmentTypedDict` schema (required keys: `name`, `skeleton`, `original`, `context`, `type`, `subtype`, `virtual_filename`, `blueprint`, `module_name`, `governance`); raise `ParseError` if `logic_code` is empty
- [ ] T026 [US1] Add `"directory_scan"` strategy to `RepoProcessor._discover_modules()` in `src/discovery/metadata_enricher.py` — scans directories recursively with `Path.rglob("*.php")`, excludes `vendor/`, `node_modules/`, `tests/`, `cache/`; activated when `ProcessingConfig.module_discovery_strategy == "directory_scan"`; **also** add `sc001_timeout_s: float = 5.0` field to `ProcessingConfig` dataclass (default matches SC-001 AMD Threadripper baseline; overridable via config for non-reference hardware — see spec.md SC-001)
- [ ] T027 [US1] Write integration test: instantiate `PhpLegacyAdapter`, run on `tests/fixtures/php_legacy/oscommerce_categories.php`, assert emitted `.txt` parses correctly via `parse_bundle()` from `src/factory/fragment_extractor.py` in `tests/integration/test_php_processor_bundles.py`

**Checkpoint**: User Story 1 fully functional — osCommerce, WordPress, ZenCart files produce valid AEGF bundles parseable by Stage 2.

---

## Phase 4: User Story 2 — Etiquetado semántico de patrones de deuda técnica (Priority: P1)

**Goal**: Every bundle contains a `[LEGACY_SIGNATURES]` section with labelled `SIGNATURE_CATEGORY` entries. Stage 2 (`parse_bundle()` and `get_v2_fragments()` in `src/factory/fragment_extractor.py`) parses and injects this section into Teacher prompt.

**Covers**: FR-003, FR-005, FR-014, FR-004 (generic section parser), FR-015 (partial)

**Independent Test**: Feed string containing `mysql_query($sql . $id)`, `global $db`, `include('header.php')`, `$_SESSION['cart']` to `scan_signatures()` → assert 4 `LegacySignature` instances with correct categories.

- [ ] T028 [P] [US2] Write unit tests for `scan_signatures` covering all 6 SIGNATURE_CATEGORY categories plus severity mapping in `tests/unit/test_php_signatures.py`
- [ ] T029 [US2] Implement 6-category regex pattern library in `src/discovery/php_signatures.py`:
  - `PERSISTENCE_SMELL`: `mysql_query`, `tep_db_query`, `$wpdb->query/prepare/get_results`, `zen_db_perform`, `Mage::getModel`
  - `STATE_POLLUTION`: `global \$\w+`, `\$_SESSION`, `\$_COOKIE`, `\$GLOBALS`, `tep_session_register`
  - `MODULE_LINK_SMELL`: `include[_once]?(`, `require[_once]?(`, string with path concatenation
  - `SECURITY_VULN`: concatenated SQL (`mysql_query.*\\.`), `echo \$_(GET|POST|REQUEST)`, `eval(`, dynamic `include(\$`
  - `CONSTANT_POLLUTION`: `define\(`, `DIR_WS_\w+`, `DIR_FS_\w+`, `TABLE_\w+`
  - `MODERN_HYBRID`: `namespace `, `^use `, `class \w+ (extends|implements)`, `->__construct(`
- [ ] T030 [US2] Implement `scan_signatures(content: str, platform_patterns: MappingProxyType) -> list[LegacySignature]` with severity classification (`SECURITY_VULN` → critical; `STATE_POLLUTION`/`PERSISTENCE_SMELL` → warning; others → info) in `src/discovery/php_signatures.py`
- [ ] T031 [US2] Implement `format_legacy_signatures_section(sigs: list[LegacySignature]) -> str` — serializes to the **multi-line key:value bundle-level format** defined in `contracts/bundle-format.md §[LEGACY_SIGNATURES]`: one block per signature with keys `CATEGORY`, `PATTERN`, `SEVERITY`, `MODERN_HINT` each on its own line, blocks separated by `---`; **NOT a CSV/table format** (the contract is authoritative, replaces the prior pipe-delimited spec) in `src/discovery/php_signatures.py`
- [ ] T032 [US2] Integrate `scan_signatures()` into `process_php_file()` in `src/discovery/php_fragmenter.py` — populate `signatures: tuple[LegacySignature, ...]` on each `PhpFragment`
- [ ] T033 [US2] Extend `write_bundle()` in `src/discovery/php_fragmenter.py` to insert the `[LEGACY_SIGNATURES]` section (from `format_legacy_signatures_section(fragment.signatures)`) **BEFORE the `--- FILE:` delimiter, NOT after fragment content**; correct bundle layout: `[ARCH_HEADER]\n{header}\n[LEGACY_SIGNATURES]\n{sigs}\n--- FILE: {name} ({type}) ---\n{raw_content}` per `contracts/bundle-format.md §Bundle Structure`
- [ ] T034 [US2] Extend `parse_bundle()` in `src/factory/fragment_extractor.py` with generic section discovery loop: `re.findall(r'\[([A-Z_]+)\](.*?)(?=\n\[|\n---|$)', text, re.DOTALL)` → store unknown sections as `extra_<name>` keys in result dict; the `\n---` sentinel prevents `--- FILE:` fragment bodies from leaking into `extra_*` keys (aligns with existing ARCH_HEADER sentinel and R-005)
- [ ] T035 [US2] Extend `get_v2_fragments()` in `src/factory/fragment_extractor.py` to inject `arch.get("extra_legacy_signatures", "")` into fragment dict's context for Teacher prompt variable `${legacy_signatures}`
- [ ] T036 [US2] Write integration test: process osCommerce fixture → parse emitted bundle via `parse_bundle()` from `src/factory/fragment_extractor.py` → assert `extra_legacy_signatures` present and contains ≥1 PERSISTENCE_SMELL entry in `tests/integration/test_php_stage2_roundtrip.py`

**Checkpoint**: User Stories 1 + 2 both work — bundles carry semantic debt labels visible to Stage 2 Teacher prompt.

---

## Phase 5: User Story 3 — Detección de dependencias implícitas (Priority: P2)

**Goal**: ARCH_HEADER field `IMPLICIT_DEPS` lists all variables used but not locally assigned in the fragment (80% heuristic).

**Covers**: FR-006

**Independent Test**: Fragment source using `$languages_id` and `$db` without local assignment → `detect_implicit_deps()` returns `tuple[ImplicitDependency, ...]` with `target_symbol` = `"$db"`, `"$languages_id"` and `confidence` = 1.0 (known-set match).

- [ ] T037 [P] [US3] Write unit tests for `detect_implicit_deps` covering all edge cases: (a) assigned vs unassigned variable; (b) superglobals excluded (`$_GET`, `$_POST`, `$_SESSION`, `$_SERVER`, `$_COOKIE`, `$GLOBALS`); (c) **function params excluded** — func receiving `$db` as param must NOT appear as implicit dep; (d) **`foreach`/`catch` vars excluded** (`foreach ($r as $k => $v)` → `$k`, `$v` excluded); (e) `$this->` property references excluded; (f) confidence 1.0 for known-set matches; (g) confidence 0.8 for frequency-scan matches in `tests/unit/test_php_fragmenter.py`
- [ ] T038 [US3] Implement `detect_implicit_deps(fragment_content: str) -> tuple[ImplicitDependency, ...]` in `src/discovery/php_fragmenter.py` — 80% heuristic with two passes:
  - **Exclusion set (applied before both passes)**: superglobals (`$_GET`, `$_POST`, `$_SESSION`, `$_SERVER`, `$_COOKIE`, `$GLOBALS`, `$_FILES`, `$_REQUEST`), PHP built-ins (`$argc`, `$argv`, `$this`), **function params** (regex `function\s+\w+\s*\(([^)]*)\)` → extract `$var` tokens), **`foreach` loop vars** (`foreach\s*\([^)]+?\s+as\s+(\$\w+)` + key vars `(\$\w+)\s*=>`), **`catch` vars** (`catch\s*\([^)]+\s+(\$\w+)\)`), locally-assigned vars (`\$var\s*=`)
  - **Pass 1 — Known-set scan**: for each var in (`$db`, `$customer_id`, `$languages_id`, `$currencies`, `$orders`, `$messageStack`, `$languages`, `$template`, `$breadcrumb`, `$application`): if present in fragment AND not in exclusion set → `ImplicitDependency(target_symbol=var, dependency_type="global_var", confidence=1.0)`
  - **Pass 2 — Frequency scan**: find `\$(\w+)` used ≥3 times AND not in exclusion set → `ImplicitDependency(target_symbol=var, dependency_type="global_var", confidence=0.8)`
  - Return sorted union by `target_symbol`; store in `PhpFragment.implicit_deps`
- [ ] T039 [US3] Wire `detect_implicit_deps()` into `process_php_file()` in `src/discovery/php_fragmenter.py` — pass result as `implicit_deps=` to `PhpFragment` constructor; extend `format_arch_header()` to serialize `IMPLICIT_DEPS: ['$var1', '$var2']` from `ImplicitDependency.target_symbol` when non-empty

---

## Phase 6: User Story 4 — Reconstrucción del grafo de módulos (Priority: P2)

**Goal**: `IncludeGraph` built from a full repository; hub files (included by ≥5 others) emit MODULE_BLUEPRINT bundles.

**Covers**: FR-007, FR-004 (INCLUDE_GRAPH section in bundle)

**Independent Test**: Build graph from 5 interconnected fixture files → assert `IncludeGraph.edges` contains correct arcs; assert hub file identified via `get_hub_files()`.

- [ ] T040 [P] [US4] Write unit tests for `parse_includes`, `build_include_graph`, `get_hub_files` in `tests/unit/test_php_include_graph.py`
- [ ] T041 [US4] Implement `parse_includes(content: str, known_constants: dict[str, str]) -> list[tuple[str, str, bool]]` in `src/discovery/php_include_graph.py` — extracts include/require paths; resolves `DIR_WS_*`/`DIR_FS_*` constants where possible; marks unresolved as `UNRESOLVED`
- [ ] T042 [US4] Implement `build_include_graph(file_map: dict[Path, str], constants: dict[str, str]) -> IncludeGraph` in `src/discovery/php_include_graph.py`
- [ ] T043 [US4] Implement `get_hub_files(graph: IncludeGraph, threshold: int = 5) -> list[str]` — returns files with in-degree ≥ threshold in `src/discovery/php_include_graph.py`
- [ ] T044 [US4] Implement `format_include_graph_section(graph: IncludeGraph, source_file: str) -> str` — emits `[INCLUDE_GRAPH]\n{src} --{type}--> {tgt}\n...` for edges from source_file in `src/discovery/php_include_graph.py`
- [ ] T045 [US4] Extend `write_bundle()` in `src/discovery/php_fragmenter.py` to append `[INCLUDE_GRAPH]` section using `format_include_graph_section()`
- [ ] T046 [US4] Emit MODULE_BLUEPRINT bundle for each hub file in `PhpLegacyAdapter` repository processing flow in `src/utils/extractors/php_legacy_adapter.py`

**Checkpoint**: User Stories 1–4 complete — bundles carry full structural context (fragments, signatures, implicit deps, module graph).

---

## Phase 7: User Story 5 — Compatibilidad multi-plataforma (Priority: P3)

**Goal**: 9 platform profiles auto-detect from repo markers; platform-specific patterns applied without cross-platform false positives.

**Covers**: FR-009, FR-010, FR-024 (platform profiles; snippets handled in Phase 8)

**Independent Test**: `detect_platform(oscommerce_repo_path)` returns profile `name == "oscommerce"`; `detect_platform(wordpress_repo_path)` returns `name == "wordpress"`; no `tep_*` patterns fire on WordPress files.

- [ ] T047 [P] [US5] Write unit tests for `detect_platform` — marker file detection, marker pattern fallback, generic_php fallback in `tests/unit/test_php_platform_profiles.py`
- [ ] T048 [P] [US5] Write unit tests for Extension Mapper dispatch in `tests/unit/test_extension_mapper.py` — `.py` routes to `_ast_fragment_list`; `.php` routes to php fragmenter; unknown extension returns empty list
- [ ] T049 [US5] Implement 9 `PlatformProfile` instances in `src/discovery/php_platform_profiles.py`:
  - `oscommerce`: markers `includes/application_top.php`, patterns `tep_db_query|tep_session_register`, snippet `oscommerce.md`
  - `oscommerce_phoenix`: markers `includes/OSC/`, patterns `OSC\\OM\\Registry|use OSC\\`, snippet `oscommerce.md` (shared, Golden Rule classifies as hybrid)
  - `wordpress`: markers `wp-config.php`, patterns `\$wpdb->|add_action|add_filter`, snippet `wordpress.md`
  - `zencart`: markers `includes/configure.php`, patterns `\bzen_` function calls (**authoritative per R-007**; `includes/application_top.php` is NOT a valid ZenCart marker — exclusive to osCommerce; using it would cause false-positive collision), snippet `zencart.md`
  - `openmage`: markers `app/Mage.php`, patterns `Mage::|Varien_`, snippet `openmage.md`
  - `prestashop`: markers `config/config.inc.php` + `PS_VERSION`, snippet `prestashop.md`
  - `codeigniter`: markers `system/core/CodeIgniter.php`, patterns `CI_Controller|CI_Model`, snippet `codeigniter.md`
  - `suitecrm`: markers `include/entryPoint.php`, patterns `SugarBean|DBManager`, snippet `suitecrm.md`
  - `generic_php`: fallback, no marker files, snippet `generic_php.md`
- [ ] T050 [US5] Implement `detect_platform(repo_path: Path) -> PlatformProfile` — checks `marker_files` first; falls back to `marker_patterns` scan on top 20 PHP files; defaults to `generic_php` in `src/discovery/php_platform_profiles.py`
- [ ] T051 [US5] Wire `detect_platform()` into `PhpLegacyAdapter` repository processing — pass detected profile name to `process_php_file()` worker in `src/utils/extractors/php_legacy_adapter.py`

**Checkpoint**: All 5 user stories complete — full vertical slice from PHP repo to annotated AEGF bundle, platform-aware.

---

## Phase 8: Prompt Templates & Symfony Hexagonal Doctrine

**Purpose**: PHP Teacher receives dedicated templates enforcing the 3-section output format (DEBT_DIAGNOSTIC / MODERN_PROPOSAL / MAPPING_LOGIC) and full hexagonal modernization doctrine. Templates loaded by `load_taxonomy()` and rendered by `build_system_with_blueprint()` in `src/factory/prompt_builder.py`.

**Covers**: FR-020, FR-021, FR-022, FR-023, FR-024 (snippets)

**Independent Test**: `taxonomy.yaml` loads without YAML parse error via `load_taxonomy()` from `src/factory/prompt_builder.py`; `master_symfony_hex.md` contains "Ports", "Adapters", "DTOs", "Doctrine ORM"; at least `oscommerce.md` contains `tep_db_query`.

- [ ] T052 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/taxonomy.yaml` — defines prompt templates `system.php_legacy.context` (doctrine injection, platform snippet injection, 3-section output instruction with strict YAML format rule) and `user.php_legacy.fragment` (fragment content + `${legacy_signatures}` + `${implicit_deps}` + `${preamble}` + `${legacy_action}` + `${platform}`)
- [ ] T053 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/master_symfony_hex.md` — Symfony hexagonal architecture doctrine master file: Ports (domain interfaces), Adapters (infrastructure implementations), DTOs, Doctrine ORM as persistence, Symfony DI Container, Event Dispatcher as event bus, Hexagonal Layer rules
- [ ] T054 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/oscommerce.md` — Anti-Patterns Mapping: `tep_db_query` → Doctrine Repository/QueryBuilder; `global $customer_id` → `UserInterface`/`TokenStorage`; `$_SESSION['cart']` → `CartService` (DI); `tep_session_register()` → Symfony session; `define(DIR_WS_*)` → `.env` parameters
- [ ] T055 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/wordpress.md` — `$wpdb->query` → Doctrine DBAL; `add_action/add_filter` → EventDispatcher; `update_option/get_option` → `.env`/config service; `wp_enqueue_script` → Webpack Encore
- [ ] T056 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/zencart.md` — `zen_db_perform` → Doctrine ORM; `$_SESSION['customer_id']` → `Security::getUser()`; `zen_redirect()` → Symfony `RedirectResponse`; `zen_mail()` → Mailer component
- [ ] T057 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/openmage.md` — `Mage::getModel()` → DI autowiring; `Varien_Object` → typed DTO; `Mage::getSingleton()` → Service; resource models → Doctrine Repository
- [ ] T058 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/prestashop.md` — `Db::getInstance()->execute()` → Doctrine; `Context::getContext()->customer` → DI UserInterface; `Tools::getValue()` → Request object with validation
- [ ] T059 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/codeigniter.md` — `$this->db->query()` → Doctrine DBAL; `$this->load->model()` → DI; `$this->session->userdata()` → Session service; CI helpers → Symfony services
- [ ] T060 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/suitecrm.md` — `SugarBean::retrieve()` → Doctrine Repository; `DBManager::getConnection()` → Doctrine DBAL; `BeanFactory::getBean()` → DI; `sugar_cache_*` → Symfony Cache
- [ ] T061 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/generic_php.md` — `mysql_query/mysqli_query` → Doctrine DBAL; `global $db` → DI DB service; `$_SESSION` → Symfony Session; `include/require` chains → Service autowiring; `define()` → `.env` + Kernel parameters
- [ ] T062 Implement doctrine+snippet loader in `src/factory/prompt_builder.py` — on PHP bundle detected (LANGUAGE field == "php" in arch dict), load `master_symfony_hex.md` + platform snippet (by `PLATFORM` field → `snippets/{platform}.md`); inject as `${doctrine}` + `${platform_snippet}` into `system.php_legacy.context` template via `build_system_with_blueprint()`
- [ ] T072 Implement `resolve_preamble_ref(arch: dict, bundle_cache: dict[str, str]) -> str` in `src/factory/fragment_extractor.py` (FR-022 / R-011 preamble injection) — reads `arch.get("PREAMBLE_REF", "")` (64-char SHA-256 hex); if set, locates the bootstrap fragment in `bundle_cache` by reversing the hash: `{hashlib.sha256(v.encode()).hexdigest(): v for v in bundle_cache.values()}`; if found and `len(content) // 4 > 800` (token proxy), truncate to first `800 * 4` characters; return preamble content string or `""` when PREAMBLE_REF absent or hash not found; call `resolve_preamble_ref()` inside `get_v2_fragments()` and inject result as `${preamble}` alongside `extra_legacy_signatures` (T035) and `implicit_deps` (T039) in `extra_fields` dict — this closes the FR-022 gap; write unit test in `tests/unit/test_php_fragmenter.py` asserting: (a) known-hash lookup returns correct content, (b) unknown hash returns `""`, (c) oversized preamble is truncated to ≤3200 chars

---

## Phase 9: Polish & Validation

**Purpose**: End-to-end validation, Validation Judge, and coverage gate.

- [ ] T063 [P] Implement Validation Judge Level 1 (structural regex + optional PHP lint) in `src/factory/pipeline_runner.py`:
  - **Structural check**: regex assert presence of `[DEBT_DIAGNOSTIC]`, `[MODERN_PROPOSAL]`, `[MAPPING_LOGIC]` section headers (SC-009: ≥90% compliance)
  - **PHP syntax lint**: extract PHP code blocks (fenced ` ```php ... ``` `) from `MODERN_PROPOSAL` section; write to `tempfile.NamedTemporaryFile` with `<?php\n` prefix; run `subprocess.run(["php", "-l", tmpfile], timeout=3)`; non-zero exit → mark `INVALID_PHP_SYNTAX`, exclude from training corpus
  - **Availability guard**: `shutil.which("php") or None`; if `None`, skip lint, emit `logger.warning("php binary not found — syntax validation disabled")`
  - Temp files cleaned in `finally` block; failures logged to `validation_failures.jsonl`
- [ ] T064 [P] Extend `tests/integration/test_php_processor_bundles.py` with SC validation tests: assert SC-001 (process osCommerce fixture <5s), SC-002 (100% of emitted bundles parse via `parse_bundle()` from `src/factory/fragment_extractor.py`), SC-007 (no fatal errors on fixture repos)
- [ ] T065 Run `pytest --cov=src/discovery/php_fragmenter --cov=src/discovery/php_signatures --cov=src/discovery/php_include_graph --cov=src/discovery/php_platform_profiles --cov=src/utils/extractors/php_legacy_adapter --cov-fail-under=90` and fix any coverage gaps to satisfy SC-008
- [ ] T066 [P] Add SC-003 validation test in `tests/integration/test_php_processor_bundles.py`: assert every emitted fragment's `raw_content` line count ≤ configured `max_fragment_lines` (default: 500) — verifies fragment size is compatible with model context window
- [ ] T067 [P] Add SC-004 validation test in `tests/integration/test_php_processor_bundles.py`: process all 3 platform fixtures (osCommerce, WordPress, ZenCart) → collect `LegacySignature` instances → assert ≥95% of manually-tagged expected signatures are detected (precision benchmark against fixture-embedded comment markers `// EXPECT_SIG: <CATEGORY>`)
- [ ] T068 [P] Add SC-005 validation test in `tests/integration/test_php_processor_bundles.py`: build `IncludeGraph` from fixture files with known include relationships → assert ≥90% of expected edges are present in `graph.edges`
- [ ] T069 [P] Add SC-006 validation test in `tests/integration/test_php_processor_bundles.py`: process mixed PHP/HTML fixture → count detected business logic signatures (functions, queries, globals) vs manually-counted total → assert ≥95% extraction rate
- [ ] T070 [P] Add AEGF project header (shebang + `Architect-Expert-Gap-Forge (AEGF)` project id + copyright + `SPDX-License-Identifier: Apache-2.0`) to every new Python source file created in Phases 2–8: `src/discovery/php_fragmenter.py`, `src/discovery/php_signatures.py`, `src/discovery/php_include_graph.py`, `src/discovery/php_platform_profiles.py`, `src/utils/extractors/php_legacy_adapter.py`; verify with `python scripts/check_headers.py --check src/discovery/php_*.py src/utils/extractors/php_legacy_adapter.py` — all must pass (Constitution §V Header Policy)
- [ ] T071 [P] Wire `scripts/check_headers.py --check` for the 5 new PHP-related Python files into `Makefile` `check-headers` target (or equivalent CI step) so header regressions are caught automatically on every PR; verify: `make check-headers` exits 0 after Phase 2–8 implementation (Constitution §V)

---

## Dependencies

```
Phase 1 (T001-T004) — Setup fixtures
  └── Phase 2 (T005-T012) — Foundational entities + utilities
        ├── Phase 3 (T013-T027) — US1 fragments + bundles + Stage 2 integration
        │     └── Phase 4 (T028-T036) — US2 signatures + Stage 2 generic parser
        │           ├── Phase 5 (T037-T039) — US3 implicit deps  [parallelizable after T020]
        │           └── Phase 6 (T040-T046) — US4 include graph  [parallelizable after T022]
        └── Phase 7 (T047-T051) — US5 platform profiles          [independent after Phase 2]
              └── Phase 8 (T052-T062) — Prompt templates + doctrine
                    └── Phase 9 (T063-T065) — Polish + validation
```

### User Story Dependencies

- **US1 (Phase 3)**: Depends on Phase 2 only — no cross-story deps. 🎯 MVP
- **US2 (Phase 4)**: Depends on US1 `process_php_file()` and `write_bundle()` existing
- **US3 (Phase 5)**: Depends on `process_php_file()` (T020) — parallelizable with US4
- **US4 (Phase 6)**: Depends on `write_bundle()` (T022) — parallelizable with US3
- **US5 (Phase 7)**: Depends on Phase 2 only — parallelizable with US1

### Parallel Opportunities per Phase

- **Phase 1**: T002+T003+T004 fully parallel
- **Phase 2**: T006+T007+T008+T010+T011 fully parallel (T005 depends on T006 for LegacySignature import)
- **Phase 3**: T013+T014 parallel → T015..T020 in wave → T021+T022 → T023 → T024+T025+T026 → T027
- **Phase 4**: T028 → T029..T031 parallel → T032+T033 → T034+T035 parallel → T036
- **Phase 7**: T047+T048 parallel → T049 → T050 → T051
- **Phase 8**: T052..T061 fully parallel → T062

---

## Implementation Strategy

**MVP scope (deliver first)**: Phases 1→2→3 only.
After Phase 3, a working PHP extractor produces bundles parseable by Stage 2 (`parse_bundle()` in `src/factory/fragment_extractor.py`). US2–US5 enrich those bundles iteratively.

| Phase | Deliverable | SC satisfied |
|-------|------------|--------------|
| 1–2 | Fixtures + entities + utilities | — |
| 3 | Bundle emission, Extension Mapper in `fragment_extractor.py`, 3-stage pipeline, `directory_scan` strategy in `metadata_enricher.py` | SC-001, SC-002, SC-003, SC-007 |
| 4 | `[LEGACY_SIGNATURES]` + generic section parser in `parse_bundle()` + injection in `get_v2_fragments()` | SC-004, SC-006 |
| 5 | IMPLICIT_DEPS in ARCH_HEADER | — |
| 6 | INCLUDE_GRAPH + MODULE_BLUEPRINT | SC-005 |
| 7 | 9 platform profiles, auto-detection | SC-007 (full) |
| 8 | PHP prompt templates in `taxonomy/php_legacy/` + doctrine via `prompt_builder.py` | SC-009 (partial) |
| 9 | Validation Judge in `pipeline_runner.py` + SC validation tests + coverage gate | SC-003, SC-004, SC-005, SC-006, SC-008, SC-009 |

---

## Summary

| Metric | Count |
|--------|-------|
| Total tasks | **72** |
| Phase 1 — Setup | 4 |
| Phase 2 — Foundational | 8 |
| Phase 3 — US1 (P1) MVP | 15 |
| Phase 4 — US2 (P1) | 9 |
| Phase 5 — US3 (P2) | 3 |
| Phase 6 — US4 (P2) | 7 |
| Phase 7 — US5 (P3) | 5 |
| Phase 8 — Prompts | 12 |
| Phase 9 — Polish | 9 |
| Parallelizable [P] tasks | 41 |
| Tasks with story label | 45 |
