# Tasks: Frontend Discovery Enhancement

## Phase 1: Core Types and Extractors

### 1.1 Create TypeScriptExtractor protocol and FrontendToken types [x]
- **Do**:
  1. Create `src/utils/extractors/extractors/base.py`
  2. Define `TypeScriptExtractor` Protocol with `extract(node, raw) -> list[FrontendToken]`
  3. Define `FrontendToken` dataclass with fields: `token_type`, `data`, `file_path`, `line_number`
  4. Define `LitComponentToken`, `I18nKeyToken`, `ServiceCallToken` subclasses
  5. Add output schemas as typed dicts/comments for each token type
- **Files**: `src/utils/extractors/extractors/base.py`
- **Done when**: Protocol and types defined matching ExtractorAdapter pattern from base.py
- **Verify**: `python -c "from src.utils.extractors.extractors.base import TypeScriptExtractor, FrontendToken; print('OK')"`
- **Commit**: `feat(extractors): add TypeScriptExtractor protocol and FrontendToken types`
- _Requirements: FR-1, FR-2, FR-3, FR-4_
- _Design: TypeScriptExtractor Protocol section_

### 1.2 Create LitComponentExtractor [x]
- **Do**:
  1. Create `src/utils/extractors/extractors/lit_component.py`
  2. Implement `LitComponentExtractor` class with `extract(node, raw) -> list[FrontendToken]`
  3. Add decorator detection: `@customElement('ha-dialog')` on class declarations
  4. Extract tag name, class name, properties, states, super_class, observed attributes
  5. Handle aliased imports (`import { customElement as ce }`)
  6. Add regex fallback patterns for ~85% coverage
- **Files**: `src/utils/extractors/extractors/lit_component.py`
- **Done when**: LitComponentExtractor detects @customElement, @property, @state decorators
- **Verify**: `grep -l "customElement\|@property\|@state" src/utils/extractors/extractors/lit_component.py`
- **Commit**: `feat(extractors): add LitComponentExtractor for @customElement detection`
- _Requirements: US-1, AC-1.1-AC-1.6, FR-2_
- _Design: LitComponentExtractor section_

### 1.3 Create I18nKeyExtractor [x]
- **Do**:
  1. Create `src/utils/extractors/extractors/i18n_key.py`
  2. Implement `I18nKeyExtractor` with `extract(node, raw) -> list[FrontendToken]`
  3. Detect `localize('key')` and `hass.localize("key")` patterns
  4. Extract key prefix for template literals (` `ui.card.${action}` `)
  5. Track context: 'localize' | 'hass.localize' | 'template_literal'
  6. Add regex fallback for ~85% coverage
- **Files**: `src/utils/extractors/extractors/i18n_key.py`
- **Done when**: I18nKeyExtractor detects localize() calls with proper context
- **Verify**: `grep -l "localize\|hass.localize" src/utils/extractors/extractors/i18n_key.py`
- **Commit**: `feat(extractors): add I18nKeyExtractor for localize() detection`
- _Requirements: US-2, AC-2.1-AC-2.5, FR-3_
- _Design: I18nKeyExtractor section_

### 1.4 Create ServiceCallExtractor [x]
- **Do**:
  1. Create `src/utils/extractors/extractors/service_call.py`
  2. Implement `ServiceCallExtractor` with `extract(node, raw) -> list[FrontendToken]`
  3. Detect `hass.callService(domain, service, data)` pattern
  4. Extract domain, service, entity_ids from serviceData
  5. Handle `this.hass`, `context._hass`, and plain `hass` prefixes
  6. Add regex fallback for ~85% coverage
- **Files**: `src/utils/extractors/extractors/service_call.py`
- **Done when**: ServiceCallExtractor extracts domain/service/entity_id tuples
- **Verify**: `grep -l "callService" src/utils/extractors/extractors/service_call.py`
- **Commit**: `feat(extractors): add ServiceCallExtractor for callService() detection`
- _Requirements: US-3, AC-3.1-AC-3.6, FR-4_
- _Design: ServiceCallExtractor section_

### 1.5 Create TranslationJsonParser [x]
- **Do**:
  1. Create `src/utils/extractors/parsers/translation_json.py`
  2. Implement `TranslationEntry` dataclass with `key`, `value`, `file_path`, `is_leaf`
  3. Implement `parse_translation_json(file_path: Path) -> list[TranslationEntry]`
  4. Recursively flatten nested JSON to dot-path keys
  5. Identify leaf nodes vs intermediate categories
  6. Handle ICU message placeholders (`{name}`, `{count, plural, =0 {Zero}}`)
- **Files**: `src/utils/extractors/parsers/translation_json.py`
- **Done when**: TranslationJsonParser flattens nested JSON correctly
- **Verify**: `python -c "from src.utils.extractors.parsers.translation_json import parse_translation_json; print('OK')"`
- **Commit**: `feat(parsers): add TranslationJsonParser for i18n JSON files`
- _Requirements: US-4, AC-4.1-AC-4.4, FR-5_
- _Design: TranslationJsonParser section_

### 1.6 V1 [VERIFY] Quality checkpoint [x]
- **Do**: Run quality checks on Phase 1 files
- **Verify**: `python -m py_compile src/utils/extractors/extractors/base.py src/utils/extractors/extractors/lit_component.py src/utils/extractors/extractors/i18n_key.py src/utils/extractors/extractors/service_call.py src/utils/extractors/parsers/translation_json.py`
- **Done when**: All files compile without syntax errors
- **Commit**: `chore(extractors): pass quality checkpoint`

---

## Phase 2: TypeScriptAdapter and Factory Integration

### 2.1 Create TypeScriptAdapter [x]
- **Do**:
  1. Create `src/utils/extractors/typescript_adapter.py`
  2. Implement `TypeScriptAdapter` class implementing `ExtractorAdapter` protocol
  3. Add `__init__(extractors: list[TypeScriptExtractor] | None = None, use_regex_fallback: bool = True)`
  4. Implement `parse_file(file_path: Path) -> ParseResult` with tree-sitter primary, regex fallback
  5. Implement `extract_dependencies(file_path: Path) -> list[Dependency]`
  6. Route .json files to TranslationJsonParser
  7. Return `ParseResult` with AST tree and FrontendToken list in metadata
- **Files**: `src/utils/extractors/typescript_adapter.py`
- **Done when**: TypeScriptAdapter.parse_file returns ParseResult with FrontendTokens
- **Verify**: `python -c "from src.utils.extractors.typescript_adapter import TypeScriptAdapter; print('OK')"`
- **Commit**: `feat(typescript): add TypeScriptAdapter implementing ExtractorAdapter protocol`
- _Requirements: FR-1_
- _Design: TypeScriptAdapter section_

### 2.2 Register TypeScript adapter in factory [x]
- **Do**:
  1. Modify `src/utils/extractors/factory.py`
  2. Add `"typescript": "src.utils.extractors.typescript_adapter.TypeScriptAdapter"` to `_ADAPTER_REGISTRY`
  3. Add `"ts": "src.utils.extractors.typescript_adapter.TypeScriptAdapter"` alias
  4. Add `"tsx": "src.utils.extractors.typescript_adapter.TypeScriptAdapter"` alias
- **Files**: `src/utils/extractors/factory.py`
- **Done when**: Factory returns TypeScriptAdapter for "typescript", "ts", "tsx" profiles
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('typescript'); print(type(a).__name__)"`
- **Commit**: `feat(factory): register TypeScriptAdapter in adapter registry`
- _Requirements: FR-6_
- _Design: Factory Registration section_

### 2.3 V2 [VERIFY] Quality checkpoint [x]
- **Do**: Run quality checks and verify adapter loads correctly
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('typescript'); assert 'TypeScriptAdapter' in type(a).__name__"`
- **Done when**: Factory integration works
- **Commit**: `chore(typescript): pass quality checkpoint`

---

## Phase 3: ChatML Exporter and Taxonomy Prompts

### 3.1 Create ChatMLExporter [x]
- **Do**:
  1. Create `src/export/chatml_exporter.py` (create directory if needed)
  2. Implement `ChatMLRecord` and `Message` dataclasses
  3. Implement `ChatMLExporter.export(tokens, system_prompt) -> Iterator[ChatMLRecord]`
  4. Implement `to_jsonl(records, output: Path) -> None`
  5. Format: `{ messages: [{role: "system"|"user"|"assistant", content: str}] }`
  6. Include schema context in system message
  7. Include source code snippet in user message
  8. Include structured JSON output in assistant message
- **Files**: `src/export/chatml_exporter.py`
- **Done when**: ChatMLExporter generates valid ChatML JSONL records
- **Verify**: `python -c "from src.export.chatml_exporter import ChatMLExporter; print('OK')"`
- **Commit**: `feat(export): add ChatMLExporter for JSONL training data`
- _Requirements: US-6, AC-6.1-AC-6.6, FR-8_
- _Design: ChatMLExporter section_

### 3.2 Create FrontendTaxonomyPrompts
- **Do**:
  1. Create `src/export/frontend_taxonomy_prompts.py`
  2. Implement `FrontendTaxonomyPrompts` dataclass with all prompt templates
  3. Add system prompts covering LitComponentExtractor output schema
  4. Add system prompts covering I18nKeyExtractor output schema
  5. Add system prompts covering ServiceCallExtractor output schema
  6. Add user prompts for each extraction type with examples
  7. Keep prompts generic (non-HomeAssistant-specific)
- **Files**: `src/export/frontend_taxonomy_prompts.py`
- **Done when**: FrontendTaxonomyPrompts contains all required prompt templates
- **Verify**: `python -c "from src.export.frontend_taxonomy_prompts import FrontendTaxonomyPrompts; print('OK')"`
- **Commit**: `feat(prompts): add FrontendTaxonomyPrompts for extraction guidance`
- _Requirements: US-7, AC-7.1-AC-7.5, FR-9_
- _Design: FrontendTaxonomyPrompts section_

### 3.3 V3 [VERIFY] Quality checkpoint [x]
- **Do**: Run quality checks on export layer
- **Verify**: `python -m py_compile src/export/chatml_exporter.py src/export/frontend_taxonomy_prompts.py`
- **Done when**: Export files compile without errors
- **Commit**: `chore(export): pass quality checkpoint`

---

## Phase 4: Configuration Updates

### 4.1 Create homeassistant_frontend.yaml discovery config [x]
- **Do**:
  1. Create `configs/stage_1_discovery/examples/homeassistant_frontend.yaml`
  2. Define `static_repos` with `home-assistant/frontend`
  3. Add `.ts` and `.tsx` to `extensions`
  4. Configure `processors` mapping for TypeScript files
  5. Set output paths following existing pattern
- **Files**: `configs/stage_1_discovery/examples/homeassistant_frontend.yaml`
- **Done when**: Config file follows existing discovery config schema
- **Verify**: `python -c "import yaml; yaml.safe_load(open('configs/stage_1_discovery/examples/homeassistant_frontend.yaml')); print('OK')"`
- **Commit**: `feat(config): add homeassistant_frontend discovery config example`
- _Requirements: US-5, AC-5.1-AC-5.5_
- _Design: File Structure section_

### 4.2 Update homeassistant.yaml with TypeScript extensions
- **Do**:
  1. Modify `configs/homeassistant.yaml`
  2. Add `"home-assistant/frontend"` to `static_repos` list
  3. Add `".ts"` and `".tsx"` to `extensions` list
- **Files**: `configs/homeassistant.yaml`
- **Done when**: homeassistant.yaml includes TypeScript extensions and frontend repo
- **Verify**: `python -c "import yaml; cfg = yaml.safe_load(open('configs/homeassistant.yaml')); assert '.ts' in cfg['extensions'] and '.tsx' in cfg['extensions']"`
- **Commit**: `feat(config): add TypeScript extensions and frontend repo to homeassistant.yaml`
- _Requirements: US-5, AC-5.2_
- _Design: Integration Points section_

### 4.3 V4 [VERIFY] Quality checkpoint [x]
- **Do**: Verify YAML configs load without errors
- **Verify**: `python -c "import yaml; yaml.safe_load(open('configs/homeassistant.yaml')); yaml.safe_load(open('configs/stage_1_discovery/examples/homeassistant_frontend.yaml')); print('OK')"`
- **Done when**: All YAML configs are valid
- **Commit**: `chore(config): pass quality checkpoint`

---

## Phase 5: Unit Tests

### 5.1 Create test_typescript_adapter.py
- **Do**:
  1. Create `tests/unit/extractors/test_typescript_adapter.py`
  2. Test parse_file returns ParseResult
  3. Test regex fallback triggers on tree-sitter failure
  4. Test .json files route to TranslationJsonParser
  5. Test extractors are called during parsing
  6. Create test fixtures for TypeScript samples
- **Files**: `tests/unit/extractors/test_typescript_adapter.py`, `tests/fixtures/typescript_samples/`
- **Done when**: All tests pass
- **Verify**: `python -m pytest tests/unit/extractors/test_typescript_adapter.py -v --tb=short 2>&1 | tail -20`
- **Commit**: `test(typescript): add unit tests for TypeScriptAdapter`
- _Requirements: Test Strategy section_
- _Design: Unit Tests section_

### 5.2 Create test_lit_component.py
- **Do**:
  1. Create `tests/unit/extractors/extractors/test_lit_component.py`
  2. Test decorator detection (customElement, property, state)
  3. Test tag name extraction from string literal
  4. Test aliased import handling
  5. Test property/state extraction
  6. Create fixture files with @customElement examples
- **Files**: `tests/unit/extractors/extractors/test_lit_component.py`, `tests/fixtures/typescript_samples/lit_component.ts`
- **Done when**: All Lit extractor tests pass
- **Verify**: `python -m pytest tests/unit/extractors/extractors/test_lit_component.py -v --tb=short 2>&1 | tail -20`
- **Commit**: `test(lit): add unit tests for LitComponentExtractor`
- _Requirements: AC-1.1-AC-1.6_
- _Design: Unit Tests section_

### 5.3 Create test_i18n_key.py [x]
- **Do**:
  1. Create `tests/unit/extractors/extractors/test_i18n_key.py`
  2. Test localize() detection
  3. Test hass.localize() detection
  4. Test template literal prefix extraction
  5. Test context tracking (localize/hass.localize/template_literal)
  6. Create fixture files with i18n call examples
- **Files**: `tests/unit/extractors/extractors/test_i18n_key.py`, `tests/fixtures/typescript_samples/i18n_calls.ts`
- **Done when**: All i18n extractor tests pass
- **Verify**: `python -m pytest tests/unit/extractors/extractors/test_i18n_key.py -v --tb=short 2>&1 | tail -20`
- **Commit**: `test(i18n): add unit tests for I18nKeyExtractor`
- _Requirements: AC-2.1-AC-2.5_
- _Design: Unit Tests section_

### 5.4 Create test_service_call.py [x]
- **Do**:
  1. Create `tests/unit/extractors/extractors/test_service_call.py`
  2. Test callService() detection
  3. Test domain/service extraction
  4. Test entity_id extraction from serviceData
  5. Test different hass prefixes (this.hass, context._hass, hass)
  6. Create fixture files with service call examples
- **Files**: `tests/unit/extractors/extractors/test_service_call.py`, `tests/fixtures/typescript_samples/service_calls.ts`
- **Done when**: All service call extractor tests pass
- **Verify**: `python -m pytest tests/unit/extractors/extractors/test_service_call.py -v --tb=short 2>&1 | tail -20`
- **Commit**: `test(service): add unit tests for ServiceCallExtractor`
- _Requirements: AC-3.1-AC-3.6_
- _Design: Unit Tests section_

### 5.5 Create test_chatml_exporter.py
- **Do**:
  1. Create `tests/unit/export/test_chatml_exporter.py`
  2. Test ChatMLRecord format
  3. Test messages array structure
  4. Test JSONL output format
  5. Test meta.source and meta.file fields
- **Files**: `tests/unit/export/test_chatml_exporter.py`
- **Done when**: test_chatml_exporter.py exists with tests
- **Verify**: `python -m pytest tests/unit/export/test_chatml_exporter.py -v --tb=short`
- **Commit**: `test(export): add unit tests for ChatMLExporter`
- _Requirements: Test Strategy section_
- _Design: Unit Tests section_

### 5.6 Create test_translation_json_parser.py [x]
- **Do**:
  1. Create `tests/unit/extractors/parsers/test_translation_json.py`
  2. Test nested JSON flattening to dot-path keys
  3. Test leaf node identification
  4. Test ICU placeholder handling
  5. Create fixture JSON files with various structures
- **Files**: `tests/unit/extractors/parsers/test_translation_json.py`, `tests/fixtures/translation_samples/`
- **Done when**: All TranslationJsonParser tests pass
- **Verify**: `python -m pytest tests/unit/extractors/parsers/test_translation_json.py -v --tb=short`
- **Commit**: `test(parser): add unit tests for TranslationJsonParser`
- _Requirements: AC-4.1-AC-4.4_
- _Design: Unit Tests section_

### 5.7 V5 [VERIFY] Quality checkpoint: all unit tests [x]
- **Do**: Run all unit tests
- **Verify**: `python -m pytest tests/unit/extractors/ tests/unit/export/ -v --tb=short`
- **Done when**: All unit tests pass (144/144)
- **Commit**: `chore(tests): pass unit test checkpoint`

---

## Phase 6: Integration and Validation

### 6.1 Integration test - TypeScriptAdapter end-to-end [x]
- **Do**:
  1. Create a sample TypeScript file with Lit component, i18n keys, and service calls
  2. Run TypeScriptAdapter.parse_file() on it
  3. Verify all extractors produce expected output
- **Files**: `tests/integration/test_typescript_adapter_e2e.py`
- **Done when**: Integration test passes
- **Verify**: `python -m pytest tests/integration/test_typescript_adapter_e2e.py -v --tb=short`
- **Commit**: `test(integration): add TypeScriptAdapter e2e integration tests`
- _Requirements: Success Criteria 1, 2_
- _Design: Integration Tests section_

### 6.2 Run validation with HomeAssistant frontend sample [x]
- **Do**:
  1. Clone or use existing home-assistant/frontend sample
  2. Run TypeScriptAdapter on sample TypeScript files
  3. Verify LitComponentExtractor detects @customElement registrations
  4. Verify I18nKeyExtractor extracts keys (target: >= 95% coverage)
  5. Verify ServiceCallExtractor extracts domain/service pairs
  6. Validate output against schema (target: 100% pass rate)
- **Done when**: Parser executes without crashes, schema validation passes
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('typescript'); result = a.parse_file(Path('path/to/sample.ts')); print(f'Parsed: {result.file_path}')"`
- **Commit**: `test(validation): run HomeAssistant frontend sample validation`
- _Requirements: Success Criteria 1-5_
- _Design: Success Criteria section_

### 6.3 Verify generic architecture (non-HomeAssistant Lit component) [x]
- **Do**:
  1. Create or obtain a non-HomeAssistant Lit component file
  2. Run TypeScriptAdapter on it without code changes
  3. Verify extraction works without HomeAssistant-specific code
- **Done when**: Generic Lit component parses and extracts correctly
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('typescript'); result = a.parse_file(Path('generic_lit.ts')); print('Generic parsing works')"`
- **Commit**: `test(generic): verify generic architecture with non-HA Lit component`
- _Requirements: Success Criteria 8, NFR-5_
- _Design: Non-Functional Requirements section_

### 6.4 V6 [VERIFY] Final quality gate [x]
- **Do**: Run full test suite and schema validation
- **Verify**: `python -m pytest tests/unit/extractors/ tests/integration/test_typescript_adapter_e2e.py tests/unit/export/ -v --tb=short 2>&1 | tail -30`
- **Done when**: All tests pass, no regressions
- **Commit**: `chore(final): pass final quality gate`

---

---

## Phase 0: Reproduce (Bug TDD)

**Goal**: Confirm the adapter selection bug exists before any code changes.

### 0.1 [VERIFY] Reproduce bug: TypeScript files skip adapter processing [x]
- **Do**:
  1. Read `src/discovery/metadata_enricher.py` lines 140-160 (adapter init) and 410-475 (adapter usage)
  2. Confirm `self._adapter = get_adapter(cfg.profile)` at line 145 selects adapter once per RepoProcessor
  3. Confirm `if mf.path.suffix == ".py":` at line 420 limits adapter to Python files only
  4. Verify TypeScript files (.ts, .tsx) are never passed to any adapter
- **Files**: `src/discovery/metadata_enricher.py`
- **Done when**: Bug confirmed - adapter selected once per repo, not per file; only .py files use adapter
- **Verify**: `grep -n "get_adapter\|self._adapter\|suffix.*\.py" src/discovery/metadata_enricher.py`
- **Commit**: None (Phase 0 - no code changes)

### 0.2 [VERIFY] Confirm repro consistency: verify bug is reproducible [x]
- **Do**:
  1. Run reproduction check: analyze code path for .ts file in metadata_enricher
  2. Confirm TypeScript files follow the non-adapter code path (skip lines 420-475)
  3. Document BEFORE state in .progress.md for VF verification
- **Done when**: Bug behavior is consistent; BEFORE state documented
- **Verify**: Code analysis confirms .ts files skip adapter
- **Commit**: `chore(bug): document reality check before fix`
- _Bug: Line 145 uses `get_adapter(cfg.profile)` once; line 420 only calls adapter for `.py` files_

---

## Phase 1: Red-Green-Yellow TDD Cycles

**Goal**: Write failing test first, then fix the bug.

### 1.1 [RED] Failing test: TypeScript files should be processed by TypeScriptAdapter [x]
- **Do**:
  1. Create test file `tests/integration/test_metadata_enricher_typescript_processing.py`
  2. Write test that verifies RepoProcessor calls adapter for .ts files
  3. Test that TypeScriptAdapter.parse_file() is invoked for .ts files (not skipped)
  4. Verify the test FAILS with current code (adapter never called for .ts)
- **Files**: `tests/integration/test_metadata_enricher_typescript_processing.py`
- **Done when**: Test exists AND fails because TypeScript files skip adapter
- **Verify**: `python -m pytest tests/integration/test_metadata_enricher_typescript_processing.py -v 2>&1 | grep -q "FAIL" && echo RED_PASS`
- **Commit**: `test(bug): red - failing test for TypeScript adapter selection`
- _Bug: metadata_enricher.py uses `cfg.profile` not file extension_

### 1.2 [GREEN] Pass test: implement per-file adapter selection
- **Do**:
  1. Modify `src/discovery/metadata_enricher.py`
  2. Remove `self._adapter = get_adapter(cfg.profile)` from `__init__` (line 145)
  3. Remove `if mf.path.suffix == ".py":` guard (line 420)
  4. Add per-file adapter selection: `adapter = get_adapter(mf.path.suffix)` inside `_process_file`
  5. Call `adapter.parse_file(mf.path)` for ALL file extensions
- **Files**: `src/discovery/metadata_enricher.py`
- **Done when**: Previously failing test now passes
- **Verify**: `python -m pytest tests/integration/test_metadata_enricher_typescript_processing.py -v`
- **Commit**: `fix(adapter): green - select adapter per file extension`
- _Requirements: Bug Fix - CRITICAL_

### 1.3 [YELLOW] Refactor: remove unused _adapter field
- **Do**:
  1. Verify `self._adapter` is no longer used after fix
  2. Remove `self._adapter` instance variable from `__init__`
  3. Ensure all code paths use per-file adapter lookup
  4. Fix the test file `tests/integration/test_metadata_enricher_typescript_processing.py` - the tests access `processor._adapter` which no longer exists. Rewrite tests to mock at the correct level or test the behavior differently.
- **Files**: `src/discovery/metadata_enricher.py`, `tests/integration/test_metadata_enricher_typescript_processing.py`
- **Done when**: Code is clean, no orphaned adapter references; tests pass
- **Verify**: `grep -n "self._adapter" src/discovery/metadata_enricher.py` returns nothing AND `python -m pytest tests/integration/test_metadata_enricher_typescript_processing.py -v` passes
- **Commit**: `refactor(adapter): yellow - remove unused _adapter field and fix tests`

### 1.4 [VERIFY] Quality checkpoint: lint and type check
- **Do**: Run lint and type check on modified file
- **Verify**: `python -m py_compile src/discovery/metadata_enricher.py && echo COMPILE_PASS`
- **Done when**: No syntax errors
- **Commit**: `chore(adapter): pass quality checkpoint`

---

## Phase 2: Additional Testing

### 2.1 Test factory extension mapping for TypeScript [x]
- **Do**:
  1. Test `get_adapter(".ts")` returns TypeScriptAdapter
  2. Test `get_adapter(".tsx")` returns TypeScriptAdapter
  3. Test `get_adapter(".py")` returns PythonAstAdapter
  4. Test unknown extensions fall back to default adapter
- **Files**: `tests/unit/test_extractors_factory.py`
- **Done when**: All factory extension mapping tests pass
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; ts = get_adapter('.ts'); print(type(ts).__name__)" | grep -q TypeScript`
- **Commit**: `test(factory): verify extension mapping for TypeScript`

### 2.2 Integration test: TypeScript file processing through full pipeline [x]
- **Do**:
  1. Create a test .ts file with Lit component, i18n keys, service calls
  2. Run RepoProcessor with the test file
  3. Verify TypeScriptAdapter.parse_file() is called
  4. Verify extraction results contain expected Lit/i18n/service call data
- **Files**: `tests/integration/test_typescript_adapter_e2e.py`
- **Done when**: Integration test passes showing TypeScript files are processed
- **Verify**: `python -m pytest tests/integration/test_typescript_adapter_e2e.py -v --tb=short`
- **Commit**: `test(integration): verify TypeScript processing in full pipeline`

### 2.3 [VERIFY] Quality checkpoint: run all tests
- **Do**: Run full test suite
- **Verify**: `python -m pytest tests/ -v --tb=short -x 2>&1 | tail -20`
- **Done when**: All tests pass, no regressions
- **Commit**: `chore(tests): pass full test suite checkpoint`

---

## Phase 3: Quality Gates

### 3.1 V3 [VERIFY] Full local CI
- **Do**: Run complete local CI suite
- **Verify**: `python -m pytest tests/ -v --tb=short && python -m py_compile src/discovery/metadata_enricher.py`
- **Done when**: All tests pass, code compiles
- **Commit**: `chore(ci): pass local CI`

### 3.2 V4 [VERIFY] CI pipeline passes
- **Do**: Verify GitHub Actions/CI passes after push
- **Verify**: `gh pr checks` shows all green
- **Done when**: CI pipeline passes
- **Commit**: None

### 3.3 V5 [VERIFY] AC checklist
- **Do**: Read requirements.md, verify adapter selection bug is fixed
- **Verify**: Code analysis confirms per-file adapter selection is implemented
- **Done when**: Bug fix verified in code
- **Commit**: None

### 3.4 Create PR and verify CI
- **Do**:
  1. Verify current branch is feature branch
  2. Push branch: `git push -u origin feat/frontend-discovery-enhancement`
  3. Create PR using gh CLI
- **Verify**: `gh pr checks --watch` (wait for CI completion)
- **Done when**: PR created, CI green
- **Commit**: None

---

## Phase 4: PR Lifecycle

### 4.1 Monitor CI and fix issues
- **Do**:
  1. Check CI status: `gh pr checks`
  2. If CI fails, read failure details and fix locally
  3. Push fixes and re-verify
- **Done when**: All CI checks pass
- **Verify**: `gh pr checks` shows all green

### 4.2 Address review comments
- **Do**: Address any code review feedback
- **Done when**: All review comments resolved
- **Verify**: `gh pr view` shows no pending comments

### VF [VERIFY] Goal verification: original failure now passes
- **Do**:
  1. Read BEFORE state from .progress.md
  2. Re-run reproduction check (code analysis)
  3. Compare output with BEFORE failure
  4. Document AFTER state in .progress.md
- **Verify**: `grep -n "self._adapter" src/discovery/metadata_enricher.py` returns nothing; per-file adapter selection confirmed
- **Done when**: Command that failed before (TypeScript skipping adapter) now shows TypeScript files are processed
- **Commit**: `chore(bug): verify fix resolves original issue`

---

## Unresolved Questions
- None (resolved in design.md)

## Notes
- POC shortcuts: Using regex fallback (~85% coverage) instead of tree-sitter AST for v1
- POC shortcuts: Tag names resolved as constants marked "unresolved" in v1
- POC shortcuts: Dynamic key prefix-only extraction for template literals
- Production TODOs: Implement tree-sitter AST parsing for v2 (~95% coverage)
- Production TODOs: Implement constant reference resolution for tag names
- Production TODOs: Add parallel extractor execution via concurrent.futures
- **BUG FIX 7.x**: Adapter selection bug - metadata_enricher uses `cfg.profile` not file extension
