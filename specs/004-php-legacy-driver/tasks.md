# Tasks: PHPLegacyDriver (Regex-Based Extractor)

**Feature Branch**: `004-php-legacy-driver`
**Generated**: 2026-03-13
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

- [ ] T005 Define `PhpFragment` + `ImplicitDependency` typed frozen dataclasses using `@dataclass(frozen=True, slots=True)` (required fields: name, fragment_type, source_file, start_line, end_line, raw_content, legacy_action, preamble_ref, dependencies[include file paths], platform_hints; default fields: file_style="LEGACY_PURE", implicit_deps=(), signatures=()) in `src/discovery/php_fragmenter.py`
- [ ] T006 [P] Define `LegacySignature` typed frozen dataclass using `@dataclass(frozen=True, slots=True)` (fields: pattern_name, category, matched_text, line_number, severity, modern_equivalent) in `src/discovery/php_signatures.py`
- [ ] T007 [P] Define `IncludeGraph` + `IncludeEdge` typed frozen dataclasses using `@dataclass(frozen=True, slots=True)` (IncludeEdge fields: source_file, target_file, include_type, line_number; IncludeGraph fields: edges `tuple[IncludeEdge, ...]`, entry_points `tuple[str, ...]`) in `src/discovery/php_include_graph.py`
- [ ] T008 [P] Define `PlatformProfile` typed frozen dataclass using `@dataclass(frozen=True, slots=True)` with `MappingProxyType` coercion in `__post_init__` via `object.__setattr__` (`slots=True` is compatible with `object.__setattr__` bypass) in `src/discovery/php_platform_profiles.py`
- [ ] T009 Implement `strip_html_markup(source: str) -> str` — extracts only `<?php ... ?>` blocks from mixed PHP/HTML/JS files in `src/discovery/php_fragmenter.py`
- [ ] T010 [P] Implement `fast_brace_scan(source: str, open_pos: int) -> int` — character-loop brace matcher returning close position or `-1` on unmatched brace; callers **MUST abort fragment extraction on `-1`**: log compact record `{source_file, name, start_line, reason: "unmatched_brace"}` to `needs_manual_review.json` and **skip the fragment entirely — do not add to output list** in `src/discovery/php_fragmenter.py`
- [ ] T011 [P] Implement `read_php_file(path: Path) -> str` — reads file with UTF-8 fallback to latin-1; logs warning on fallback; raises `PhpReadError` if both fail in `src/discovery/php_fragmenter.py`
- [ ] T012 Write unit tests covering `strip_html_markup`, `fast_brace_scan` (matched, unmatched, nested), and `read_php_file` (utf8, latin1, binary) in `tests/unit/test_php_fragmenter.py`

**Checkpoint**: Core types and low-level utilities are ready. User story phases can now run in parallel.

---

## Phase 3: User Story 1 — Extracción de fragmentos PHP legacy (Priority: P1) 🎯 MVP

**Goal**: `PhpLegacyAdapter` processes a PHP repository → emits `.txt` bundles with valid `[ARCH_HEADER]` parseable by Stage 2, fragmented by heuristic blocks (functions, switch/case, Preamble Rule), via 3-stage parallel pipeline.

**Covers**: FR-001, FR-002, FR-008, FR-011, FR-012, FR-013, FR-015, FR-016, FR-017, FR-018, FR-019

**Independent Test**: Run `PhpLegacyAdapter.process_repository(oscommerce_path)` on the osCommerce fixture directory → assert at least one `.txt` emitted; assert `parse_bundle()` returns non-empty result with `MODULE` and `FRAGMENT_TYPE` fields.

- [ ] T013 [P] [US1] Write unit tests for `_extract_function_blocks`, `_extract_preamble`, `_extract_switch_cases`, `_fragment_by_size` in `tests/unit/test_php_fragmenter.py`
- [ ] T014 [P] [US1] Write unit tests for `PhpLegacyAdapter` constructor, `parse_file()` signature, and `extract_dependencies()` shape in `tests/unit/test_php_legacy_adapter.py`
- [ ] T015 [US1] Implement `_extract_preamble(source: str) -> tuple[str, str]` — returns `(preamble_content, remaining_source)`; computes `sha256(preamble_content.encode()).hexdigest()` for `preamble_ref` in `src/discovery/php_fragmenter.py`
- [ ] T016 [US1] Implement `_extract_function_blocks(source: str) -> list[tuple[int, int, str]]` — regex `function\s+\w+\s*\(` detection; uses `fast_brace_scan` to find closing brace; **if scanner returns `-1`, abort this function block**: log `{source_file, function_name, start_line, reason: "unmatched_brace"}` to `needs_manual_review.json`, do NOT yield an invalid fragment into the pipeline in `src/discovery/php_fragmenter.py`
- [ ] T017 [US1] Implement `_extract_switch_cases(source: str) -> list[tuple[int, int, str, str]]` — returns `(start, end, raw, case_label)`; sub-chunks cases >500 lines preserving case header as context; **if `fast_brace_scan` fails on the enclosing switch brace, abort the entire switch block**: log `{source_file, "switch", start_line, reason: "unmatched_switch_brace"}` to `needs_manual_review.json` and continue to the next file section in `src/discovery/php_fragmenter.py`
- [ ] T018 [US1] Implement `_fragment_by_size(source: str, max_lines: int, overlap: int = 20) -> list[tuple[int, int, str]]` — size-based fallback with context overlap for files with no function/case delimiters in `src/discovery/php_fragmenter.py`
- [ ] T019 [US1] Implement `_classify_file_style(source: str) -> str` — returns `"LEGACY_PURE"` / `"LEGACY_MODERNIZED"` / `"HYBRID"` based on presence of `namespace`, `use`, class declarations vs procedural patterns in `src/discovery/php_fragmenter.py`; wire return value into `PhpFragment.file_style` inside `process_php_file()`
- [ ] T020 [US1] Implement top-level serializable entry point `process_php_file(path: Path, content: str, profile_name: str) -> list[PhpFragment]` in `src/discovery/php_fragmenter.py` — must be a module-level function (not lambda/closure) for `pickle` compatibility with `ProcessPoolExecutor`
- [ ] T021 [US1] Implement ARCH_HEADER formatter `format_arch_header(fragment: PhpFragment) -> str` producing all required fields (MODULE, REPO_PREFIX, FILE_ROLE, FRAGMENT_TYPE, LOCAL_IMPORTS, DEPENDENCIES, NEIGHBORS, IMPLICIT_DEPS, LEGACY_ACTION, PREAMBLE_REF) in `src/discovery/php_fragmenter.py`
- [ ] T022 [US1] Implement `write_bundle(fragment: PhpFragment, output_dir: Path) -> Path` — writes `[ARCH_HEADER]\n{header}\n[SOURCE]\n{raw_content}` to `.txt` file; all fragments passed to this function are structurally valid (malformed fragments are aborted at extraction in T016/T017 and never reach `write_bundle`) in `src/discovery/php_fragmenter.py`
- [ ] T023 [US1] Implement `PhpLegacyAdapter` in `src/utils/extractors/php_legacy_adapter.py` — wraps 3-stage pipeline: `ThreadPoolExecutor(max_workers=32)` for IO reads → `ProcessPoolExecutor(os.cpu_count(), chunksize=50)` for CPU fragmentation → `ThreadPoolExecutor(max_workers=16)` for writes
- [ ] T024 [US1] Register `PhpLegacyAdapter` in `src/utils/extractors/factory.py` under key `"php_legacy"`
- [ ] T025 [US1] Add `_EXTENSION_FRAGMENTERS: dict[str, Callable]` Extension Mapper to `src/factory/production_v11.py` — `{".py": _ast_fragment_list, ".php": _php_fragment_list}`; replace hardcoded `ast.parse()` dispatch with `_EXTENSION_FRAGMENTERS.get(suffix)` lookup
- [ ] T026 [US1] Write integration test: instantiate `PhpLegacyAdapter`, run on `tests/fixtures/php_legacy/oscommerce_categories.php`, assert emitted `.txt` parses correctly via existing `parse_bundle()` in `tests/integration/test_php_processor_bundles.py`

**Checkpoint**: User Story 1 fully functional — osCommerce, WordPress, ZenCart files produce valid AEGF bundles.

---

## Phase 4: User Story 2 — Etiquetado semántico de patrones de deuda técnica (Priority: P1)

**Goal**: Every bundle contains a `[LEGACY_SIGNATURES]` section with correctly labelled `SIGNATURE_CATEGORY` (PERSISTENCE_SMELL, STATE_POLLUTION, MODULE_LINK_SMELL, SECURITY_VULN, CONSTANT_POLLUTION, MODERN_HYBRID). Stage 2 parses and injects this section into the Teacher prompt.

**Covers**: FR-003, FR-005, FR-014, FR-004 (generic section parser), FR-015 (partial)

**Independent Test**: Feed a string containing `mysql_query($sql . $id)`, `global $db`, `include('header.php')`, `$_SESSION['cart']` to signature scanner → assert 4 `LegacySignature` instances with correct categories.

- [ ] T027 [P] [US2] Write unit tests for `scan_signatures` covering all 6 categories plus severity mapping in `tests/unit/test_php_signatures.py`
- [ ] T028 [US2] Implement 6-category regex pattern library in `src/discovery/php_signatures.py`:
  - `PERSISTENCE_SMELL`: `mysql_query`, `tep_db_query`, `$wpdb->query/prepare/get_results`, `zen_db_perform`
  - `STATE_POLLUTION`: `global \$\w+`, `\$_SESSION`, `\$_COOKIE`, `\$GLOBALS`, `tep_session_register`
  - `MODULE_LINK_SMELL`: `include[_once]?(`, `require[_once]?(`, string with path concatenation
  - `SECURITY_VULN`: concatenated SQL (`mysql_query.*\\.`), `echo \$_(GET|POST|REQUEST)`, `eval(`, dynamic `include(\$`
  - `CONSTANT_POLLUTION`: `define\(`, `DIR_WS_\w+`, `DIR_FS_\w+`, `TABLE_\w+`
  - `MODERN_HYBRID`: `namespace `, `^use `, `class \w+ (extends|implements)`, `->__construct(`
- [ ] T029 [US2] Implement `scan_signatures(content: str, platform_patterns: MappingProxyType) -> list[LegacySignature]` with severity classification (`SECURITY_VULN` → critical; `STATE_POLLUTION`/`PERSISTENCE_SMELL` → warning; others → info) in `src/discovery/php_signatures.py`
- [ ] T030 [US2] Implement `format_legacy_signatures_section(sigs: list[LegacySignature]) -> str` — serializes to `[LEGACY_SIGNATURES]\nCATEGORY | LINE | SEVERITY | PATTERN | TEXT\n...` format per bundle-format contract in `src/discovery/php_signatures.py`
- [ ] T031 [US2] Integrate `scan_signatures()` into `process_php_file()` in `src/discovery/php_fragmenter.py` — populate `signatures: tuple[LegacySignature, ...]` on each `PhpFragment`
- [ ] T032 [US2] Extend `write_bundle()` in `src/discovery/php_fragmenter.py` to append `[LEGACY_SIGNATURES]` section from fragment's `signatures` field after `[SOURCE]`
- [ ] T033 [US2] Extend `parse_bundle()` in `src/factory/production_v11.py` with generic section discovery loop: `re.findall(r'\[([A-Z_]+)\]\n(.*?)(?=\n\[|\Z)', text, re.DOTALL)` → store unknown sections in `extra_sections: dict[str, str]`
- [ ] T034 [US2] Extend `get_v2_fragments()` in `src/factory/production_v11.py` to inject `extra_sections.get("LEGACY_SIGNATURES", "")` into Teacher prompt context variable `${legacy_signatures}`
- [ ] T035 [US2] Write integration test: process osCommerce fixture → parse emitted bundle → assert `extra_sections["LEGACY_SIGNATURES"]` present and contains ≥1 PERSISTENCE_SMELL entry in `tests/integration/test_php_stage2_roundtrip.py`

**Checkpoint**: User Stories 1 + 2 both work — bundles carry semantic debt labels visible to the Teacher.

---

## Phase 5: User Story 3 — Detección de dependencias implícitas (Priority: P2)

**Goal**: ARCH_HEADER field `IMPLICIT_DEPS` lists all variables used but not locally assigned in the fragment.

**Covers**: FR-006

**Independent Test**: Fragment source using `$languages_id` and `$db` without local assignment → `detect_implicit_deps()` returns `("$db", "$languages_id")`.

- [ ] T036 [P] [US3] Write unit tests for `detect_implicit_deps` — assigned vs unassigned, superglobals excluded, parameter variables excluded in `tests/unit/test_php_fragmenter.py`
- [ ] T037 [US3] Implement `detect_implicit_deps(fragment_content: str) -> tuple[str, ...]` in `src/discovery/php_fragmenter.py` using an **80% heuristic** (pragmatic over exhaustive):
  - **Pass 1 — Known-set scan**: check for presence of the most common cross-file implicit vars across multi_legacy: `$db`, `$customer_id`, `$languages_id`, `$currencies`, `$orders`, `$messageStack`, `$languages`, `$template`, `$breadcrumb`, `$application`
  - **Pass 2 — Frequency scan**: find `\$(\w+)` used ≥3 times AND not locally assigned (`\$var\s*=`) AND not a superglobal (`_GET|_POST|_SESSION|_SERVER|_COOKIE|_GLOBALS|_FILES|_REQUEST`)
  - Return sorted union of both passes; store in `PhpFragment.implicit_deps`; accept false negatives — 80% coverage is the target, not perfection
- [ ] T038 [US3] Extend `format_arch_header()` in `src/discovery/php_fragmenter.py` to include `IMPLICIT_DEPS: ['$var1', '$var2']` line when `fragment.implicit_deps` is non-empty; call `detect_implicit_deps(fragment.raw_content)` inside `process_php_file()` and pass result as `implicit_deps=` to `PhpFragment` constructor

---

## Phase 6: User Story 4 — Reconstrucción del grafo de módulos (Priority: P2)

**Goal**: `IncludeGraph` built from a full repository; hub files (included by ≥5 others) emit MODULE_BLUEPRINT bundles.

**Covers**: FR-007, FR-004 (INCLUDE_GRAPH section in bundle)

**Independent Test**: Build graph from 5 interconnected fixture files → assert `IncludeGraph.edges` contains correct arcs; assert hub file produces MODULE_BLUEPRINT bundle.

- [ ] T039 [P] [US4] Write unit tests for `parse_includes`, `build_include_graph`, `get_hub_files` in `tests/unit/test_php_include_graph.py`
- [ ] T040 [US4] Implement `parse_includes(content: str, known_constants: dict[str, str]) -> list[tuple[str, bool]]` in `src/discovery/php_include_graph.py` — extracts include/require paths; resolves `DIR_WS_*`/`DIR_FS_*` constants where possible; marks unresolved as `UNRESOLVED`
- [ ] T041 [US4] Implement `build_include_graph(file_map: dict[Path, str], constants: dict[str, str]) -> IncludeGraph` in `src/discovery/php_include_graph.py`
- [ ] T042 [US4] Implement `get_hub_files(graph: IncludeGraph, threshold: int = 5) -> list[Path]` — returns files with in-degree ≥ threshold in `src/discovery/php_include_graph.py`
- [ ] T043 [US4] Implement `format_include_graph_section(graph: IncludeGraph, source_file: Path) -> str` — emits `[INCLUDE_GRAPH]\n{src} -> {tgt} [{resolved|UNRESOLVED}]\n...` for edges from source_file in `src/discovery/php_include_graph.py`
- [ ] T044 [US4] Extend `write_bundle()` in `src/discovery/php_fragmenter.py` to append `[INCLUDE_GRAPH]` section
- [ ] T045 [US4] Emit MODULE_BLUEPRINT bundle for each hub file in `PhpLegacyAdapter.process_repository()` in `src/utils/extractors/php_legacy_adapter.py`

**Checkpoint**: User Stories 1–4 complete — bundles carry full structural context (fragments, signatures, implicit deps, module graph).

---

## Phase 7: User Story 5 — Compatibilidad multi-plataforma (Priority: P3)

**Goal**: 9 platform profiles auto-detect from repo markers; platform-specific patterns applied without cross-platform false positives.

**Covers**: FR-009, FR-010, FR-024 (platform profiles; snippets handled in Phase 8)

**Independent Test**: `detect_platform(oscommerce_repo_path)` returns profile `name == "oscommerce"`; `detect_platform(wordpress_repo_path)` returns `name == "wordpress"`; no tep_* patterns fire on WordPress files.

- [ ] T046 [P] [US5] Write unit tests for `detect_platform` — marker file detection, marker pattern fallback, generic_php fallback in `tests/unit/test_php_platform_profiles.py`
- [ ] T047 [P] [US5] Write unit tests for Extension Mapper dispatch in `tests/unit/test_extension_mapper.py` — `.py` routes to ast fragmenter; `.php` routes to php fragmenter; unknown extension returns None
- [ ] T048 [US5] Implement 9 `PlatformProfile` instances in `src/discovery/php_platform_profiles.py`:
  - `oscommerce`: markers `includes/configure.php`, patterns `tep_db_query\|tep_session_register`, snippet `oscommerce.md`
  - `oscommerce_phoenix`: markers `includes/OSC/`, patterns `OSC\\OM\\Registry\|use OSC\\`, snippet `oscommerce.md` (shared, Golden Rule)
  - `wordpress`: markers `wp-config.php`, patterns `\$wpdb->\|add_action\|add_filter`, snippet `wordpress.md`
  - `zencart`: markers `includes/application_top.php` + `zen_` function density heuristic, snippet `zencart.md`
  - `openmage`: markers `app/Mage.php`, patterns `Mage::\|Varien_`, snippet `openmage.md`
  - `prestashop`: markers `config/config.inc.php` + `PS_VERSION`, snippet `prestashop.md`
  - `codeigniter`: markers `system/codeigniter/core/`, patterns `CI_Controller\|CI_Model`, snippet `codeigniter.md`
  - `suitecrm`: markers `include/entryPoint.php`, patterns `SugarBean\|DBManager`, snippet `suitecrm.md`
  - `generic_php`: fallback, no marker files, snippet `generic_php.md`
- [ ] T049 [US5] Implement `detect_platform(repo_path: Path) -> PlatformProfile` — checks `marker_files` existence first; falls back to `marker_patterns` scan on top 20 PHP files; falls back to `generic_php` in `src/discovery/php_platform_profiles.py`
- [ ] T050 [US5] Wire `detect_platform()` into `PhpLegacyAdapter.process_repository()` — pass detected profile name to `process_php_file()` worker in `src/utils/extractors/php_legacy_adapter.py`

**Checkpoint**: All 5 user stories complete — full vertical slice from PHP repo to annotated AEGF bundle, platform-aware.

---

## Phase 8: Prompt Templates & Symfony Hexagonal Doctrine

**Purpose**: PHP Teacher receives dedicated templates enforcing the 3-section output format (DEBT_DIAGNOSTIC / MODERN_PROPOSAL / MAPPING_LOGIC) and full hexagonal modernization doctrine.

**Covers**: FR-020, FR-021, FR-022, FR-023, FR-024 (snippets)

**Independent Test**: `taxonomy.yaml` loads without YAML parse error; `master_symfony_hex.md` contains "Ports", "Adapters", "DTOs", "Doctrine ORM"; at least oscommerce.md contains `tep_db_query`.

- [ ] T051 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/taxonomy.yaml` — defines prompt templates `system.php_legacy.context` (doctrine injection, platform snippet injection, 3-section output instruction) and `user.php_legacy.fragment` (fragment content + `${legacy_signatures}` + `${implicit_deps}` + `${preamble}` + `${legacy_action}` + `${platform}`)
- [ ] T052 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/master_symfony_hex.md` — Symfony hexagonal architecture doctrine master file: Ports (domain interfaces), Adapters (infrastructure implementations), DTOs, Doctrine ORM as persistence, Symfony DI Container, Event Dispatcher as event bus, Hexagonal Layer rules
- [ ] T053 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/oscommerce.md` — Anti-Patterns Mapping: `tep_db_query` → Doctrine Repository/QueryBuilder; `global $customer_id` → `UserInterface`/`TokenStorage`; `$_SESSION['cart']` → `CartService` (DI); `tep_session_register()` → remove (Symfony session automatic); `define(DIR_WS_*)` → `.env` parameters
- [ ] T054 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/wordpress.md` — `$wpdb->query` → Doctrine DBAL; `add_action/add_filter` → EventDispatcher; `update_option/get_option` → `.env`/config service; `wp_enqueue_script` → Webpack Encore
- [ ] T055 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/zencart.md` — `zen_db_perform` → Doctrine ORM; `$_SESSION['customer_id']` → `Security::getUser()`; `zen_redirect()` → Symfony `RedirectResponse`; `zen_mail()` → Mailer component
- [ ] T056 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/openmage.md` — `Mage::getModel()` → DI autowiring; `Varien_Object` → typed DTO; `Mage::getSingleton()` → Service; resource models → Doctrine Repository
- [ ] T057 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/prestashop.md` — `Db::getInstance()->execute()` → Doctrine; `Context::getContext()->customer` → DI UserInterface; `Tools::getValue()` → Request object with validation
- [ ] T058 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/codeigniter.md` — `$this->db->query()` → Doctrine DBAL; `$this->load->model()` → DI; `$this->session->userdata()` → Session service; CI helpers → Symfony services
- [ ] T059 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/suitecrm.md` — `SugarBean::retrieve()` → Doctrine Repository; `DBManager::getConnection()` → Doctrine DBAL; `BeanFactory::getBean()` → DI; `sugar_cache_*` → Symfony Cache
- [ ] T060 [P] Create `configs/stage_2_factory/taxonomy/php_legacy/snippets/generic_php.md` — `mysql_query/mysqli_query` → Doctrine DBAL; `global $db` → DI DB service; `$_SESSION` → Symfony Session; `include/require` chains → Service autowiring; `define()` → `.env` + Kernel parameters
- [ ] T061 Implement doctrine loader in `src/factory/production_v11.py` — on PHP bundle detected, load `master_symfony_hex.md` + platform snippet (by `PlatformProfile.snippet_path`); inject as `${doctrine}` + `${platform_snippet}` into `system.php_legacy.context` template

---

## Phase 9: Polish & Validation

**Purpose**: End-to-end validation, Validation Judge, and coverage gate.

- [ ] T062 [P] Implement Validation Judge Level 1 (regex + PHP lint) in `src/factory/production_v11.py`:
  - **Structural check**: assert presence of `DEBT_DIAGNOSTIC`, `MODERN_PROPOSAL`, `MAPPING_LOGIC` section headers (SC-009: ≥90% compliance)
  - **PHP syntax lint**: extract PHP code blocks (` ```php ... ``` ` fenced) from the `MODERN_PROPOSAL` section; write each block to a `tempfile.NamedTemporaryFile` prefixed with `<?php\n`; run `subprocess.run(["php", "-l", tmpfile], timeout=3)`; if exit code ≠ 0 → mark pair `INVALID_PHP_SYNTAX` and **exclude from training corpus** (do not forward to Stage 3)
  - **Availability guard**: `shutil.which("php") or None`; if `None`, skip lint and emit `logging.warning("php binary not found — syntax validation disabled")`
  - Temp files cleaned in `finally` block; failures logged to `validation_failures.jsonl` as `{reason, teacher_response_hash, source_bundle, lint_output}`
- [ ] T063 [P] Extend `tests/integration/test_php_processor_bundles.py` with SC validation tests: assert SC-001 (process osCommerce fixture <5s), SC-002 (100% of emitted bundles parse via `parse_bundle()`), SC-007 (no fatal errors on any of the 7 multi_legacy repos)
- [ ] T064 Run `pytest --cov=src/discovery/php_fragmenter --cov=src/discovery/php_signatures --cov=src/discovery/php_include_graph --cov=src/discovery/php_platform_profiles --cov=src/utils/extractors/php_legacy_adapter --cov-fail-under=90` and fix any gaps to satisfy SC-008

---

## Dependencies

```
Phase 1 (T001-T004)
  └── Phase 2 (T005-T012)       # foundational entities + utilities
        ├── Phase 3 (T013-T026) # US1 — fragments + bundles      [starts after Phase 2]
        │     └── Phase 4 (T027-T035) # US2 — signatures + Stage2 [depends on US1 ARCH_HEADER]
        │           ├── Phase 5 (T036-T038) # US3 — implicit deps  [parallelizable after T020]
        │           └── Phase 6 (T039-T045) # US4 — include graph  [parallelizable after T022]
        └── Phase 7 (T046-T050)  # US5 — platform profiles       [independent after Phase 2]
              └── Phase 8 (T051-T061)  # Prompt templates          [independent, [P] internally]
                    └── Phase 9 (T062-T064)  # Polish + validation
```

**Parallelization opportunities per story**:
- Phase 3 (US1): T013+T014 → T015..T020 in wave → T021+T022 → T023 → T024+T025 → T026
- Phase 4 (US2): T027 → T028..T030 → T031 → T032+T033+T034 → T035
- Phase 5+6 (US3+US4): Entirely parallelizable after T021 (US1 complete)
- Phase 7 (US5): Entirely parallelizable after Phase 2
- Phase 8 (Templates): T051..T060 are fully parallel; T061 depends on all ten files

---

## Implementation Strategy

**MVP scope (deliver first)**: Phases 1→2→3 only.  
After Phase 3, a working PHP extractor produces bundles parseable by Stage 2. US2–US5 enrich those bundles iteratively.

| Phase | Deliverable | SC satisfied |
|-------|------------|--------------|
| 1–2 | Fixtures + entities + utilities | — |
| 3 | Bundle emission, Extension Mapper, 3-stage pipeline | SC-001, SC-002, SC-003, SC-007 |
| 4 | `[LEGACY_SIGNATURES]` + Stage 2 injection | SC-004, SC-006 |
| 5 | IMPLICIT_DEPS in ARCH_HEADER | — |
| 6 | INCLUDE_GRAPH + MODULE_BLUEPRINT | SC-005 |
| 7 | 9 platform profiles, auto-detection | SC-007 (full) |
| 8 | PHP prompt templates + doctrine | SC-009 (partial) |
| 9 | Validation Judge + coverage gate | SC-008, SC-009 |

---

## Summary

| Metric | Count |
|--------|-------|
| Total tasks | **64** |
| Phase 1 — Setup | 4 |
| Phase 2 — Foundational | 8 |
| Phase 3 — US1 (P1) | 14 |
| Phase 4 — US2 (P1) | 9 |
| Phase 5 — US3 (P2) | 3 |
| Phase 6 — US4 (P2) | 7 |
| Phase 7 — US5 (P3) | 5 |
| Phase 8 — Prompts | 11 |
| Phase 9 — Polish | 3 |
| Parallelizable [P] tasks | 34 |
| Tasks with story label | 44 |
