# Tasks: Frontend Discovery Enhancement

## Phase 1: Core Types and Extractors

### 1.1 Create TypeScriptExtractor protocol and FrontendToken types [DONE]
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

### 1.2 Create LitComponentExtractor [DONE]
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

### 1.3 Create I18nKeyExtractor [DONE]
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

### 1.4 Create ServiceCallExtractor [DONE]
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

### 1.5 Create TranslationJsonParser [DONE]
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

### 1.6 V1 [VERIFY] Quality checkpoint [DONE]
- **Do**: Run quality checks on Phase 1 files
- **Verify**: `python -m py_compile src/utils/extractors/extractors/base.py src/utils/extractors/extractors/lit_component.py src/utils/extractors/extractors/i18n_key.py src/utils/extractors/extractors/service_call.py src/utils/extractors/parsers/translation_json.py`
- **Done when**: All files compile without syntax errors
- **Commit**: `chore(extractors): pass quality checkpoint`

---

## Phase 2: TypeScriptAdapter and Factory Integration

### 2.1 Create TypeScriptAdapter [DONE]
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

### 2.2 Register TypeScript adapter in factory [DONE]
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

### 2.3 V2 [VERIFY] Quality checkpoint [DONE]
- **Do**: Run quality checks and verify adapter loads correctly
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('typescript'); assert 'TypeScriptAdapter' in type(a).__name__"`
- **Done when**: Factory integration works
- **Commit**: `chore(typescript): pass quality checkpoint`

---

## Phase 3: ChatML Exporter and Taxonomy Prompts

### 3.1 Create ChatMLExporter [DONE]
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

### 3.3 V3 [VERIFY] Quality checkpoint [DONE]
- **Do**: Run quality checks on export layer
- **Verify**: `python -m py_compile src/export/chatml_exporter.py src/export/frontend_taxonomy_prompts.py`
- **Done when**: Export files compile without errors
- **Commit**: `chore(export): pass quality checkpoint`

---

## Phase 4: Configuration Updates

### 4.1 Create homeassistant_frontend.yaml discovery config [DONE]
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

### 4.3 V4 [VERIFY] Quality checkpoint [DONE]
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

### 5.3 Create test_i18n_key.py [DONE]
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

### 5.4 Create test_service_call.py [DONE]
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

### 5.6 Create test_translation_json_parser.py [DONE]
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

### 5.7 V5 [VERIFY] Quality checkpoint: all unit tests [DONE]
- **Do**: Run all unit tests
- **Verify**: `python -m pytest tests/unit/extractors/ tests/unit/export/ -v --tb=short`
- **Done when**: All unit tests pass (144/144)
- **Commit**: `chore(tests): pass unit test checkpoint`

---

## Phase 6: Integration and Validation

### 6.1 Create integration test for TypeScript parsing pipeline
- **Do**:
  1. Create `tests/integration/test_typescript_processor_pipeline.py`
  2. Test end-to-end parsing of sample .ts file through TypeScriptAdapter
  3. Test ChatML JSONL output validation against schema
  4. Test config loading with new profile
  5. Use real HomeAssistant frontend sample files (or create representative fixtures)
- **Files**: `tests/integration/test_typescript_processor_pipeline.py`
- **Done when**: Integration tests pass with real TypeScript files
- **Verify**: `python -m pytest tests/integration/test_typescript_processor_pipeline.py -v --tb=short 2>&1 | tail -20`
- **Commit**: `test(integration): add TypeScript processor integration tests`
- _Requirements: Success Criteria 1, 2_
- _Design: Integration Tests section_

### 6.2 Run validation with HomeAssistant frontend sample
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

### 6.3 Verify generic architecture (non-HomeAssistant Lit component)
- **Do**:
  1. Create or obtain a non-HomeAssistant Lit component file
  2. Run TypeScriptAdapter on it without code changes
  3. Verify extraction works without HomeAssistant-specific code
- **Done when**: Generic Lit component parses and extracts correctly
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('typescript'); result = a.parse_file(Path('generic_lit.ts')); print('Generic parsing works')"`
- **Commit**: `test(generic): verify generic architecture with non-HA Lit component`
- _Requirements: Success Criteria 8, NFR-5_
- _Design: Non-Functional Requirements section_

### 6.4 V6 [VERIFY] Final quality gate
- **Do**: Run full test suite and schema validation
- **Verify**: `python -m pytest tests/unit/extractors/ tests/integration/test_typescript_processor_pipeline.py -v --tb=short 2>&1 | tail -30`
- **Done when**: All tests pass, no regressions
- **Commit**: `chore(final): pass final quality gate`

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
