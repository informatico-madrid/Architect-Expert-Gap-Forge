# Requirements: Frontend Discovery Enhancement

## Goal

Add generic TypeScript/Lit frontend parsing to the data factory pipeline, enabling ingestion of HomeAssistant frontend files (and any Lit-based frontend) for extraction of custom elements, i18n keys, and service calls into structured training data.

## User Stories

### US-1: Parse Lit Custom Elements from TypeScript
**As a** data curator
**I want to** extract `@customElement` decorated classes from TypeScript/TSX files
**So that** I can build a component registry with tag names, properties, and metadata for training

**Acceptance Criteria:**
- [ ] AC-1.1: Parser detects `customElement('ha-dialog')` decorator on class declarations
- [ ] AC-1.2: Parser extracts tag name from decorator argument (string literal or constant reference)
- [ ] AC-1.3: Parser extracts class name, property types, default values, and `@property` options (attribute, reflect, state)
- [ ] AC-1.4: Parser extracts `@state` decorated properties as reactive state
- [ ] AC-1.5: Parser handles aliased imports (`import { customElement as ce }`) and namespace imports
- [ ] AC-1.6: Output schema: `{ tag, class_name, file_path, properties[], states[], super_class }`

### US-2: Extract i18n Keys from TypeScript Code
**As a** data curator
**I want to** extract `localize()` and `hass.localize()` calls from TypeScript files
**So that** I can map translation keys to their usage contexts for localization training

**Acceptance Criteria:**
- [ ] AC-2.1: Parser detects `localize('ui.panel.lovelace.strategy.view.grid')` pattern
- [ ] AC-2.2: Parser detects `hass.localize("ui.panel.lovelace.strategy.view.grid")` pattern
- [ ] AC-2.3: Parser handles template literal keys (e.g., `` `ui.card.${action}` ``) by extracting prefix
- [ ] AC-2.4: Parser extracts key prefix for dynamic interpolation cases
- [ ] AC-2.5: Output schema: `{ key, context: 'localize'|'hass.localize'|'template_literal', line_number }`

### US-3: Extract Service Calls from TypeScript Code
**As a** data curator
**I want to** extract `hass.callService()` invocations from TypeScript files
**So that** I can build a domain/service/action vocabulary for smart home training

**Acceptance Criteria:**
- [ ] AC-3.1: Parser detects `hass.callService(domain, service, data)` pattern
- [ ] AC-3.2: Parser extracts domain string literal (e.g., "cover", "light", "climate")
- [ ] AC-3.3: Parser extracts service string literal (e.g., "open_cover", "turn_on")
- [ ] AC-3.4: Parser extracts serviceData object with entity_id when present
- [ ] AC-3.5: Parser handles `this.hass`, `context._hass`, and plain `hass` variable prefixes
- [ ] AC-3.6: Output schema: `{ domain, service, entity_ids[], file_path, line_number }`

### US-4: Parse Translation JSON Files
**As a** data curator
**I want to** flatten nested translation JSON files into key-value pairs
**So that** I can associate i18n keys with their translated text values

**Acceptance Criteria:**
- [ ] AC-4.1: Parser recursively flattens nested JSON to dot-path keys (e.g., `ui.panel.lovelace.strategy.view.grid`)
- [ ] AC-4.2: Parser identifies leaf nodes (string-only values) vs intermediate categories (nested dicts)
- [ ] AC-4.3: Parser handles ICU message format placeholders (`{name}`, `{count, plural, =0 {Zero}}`)
- [ ] AC-4.4: Output schema: `{ key, value, file_path, is_leaf }`

### US-5: Configure Discovery Pipeline for Frontend Files
**As a** data engineer
**I want to** add frontend repos to the discovery config with proper glob patterns and processors
**So that** the pipeline automatically discovers and processes TypeScript files

**Acceptance Criteria:**
- [ ] AC-5.1: Discovery config accepts `static_repos` list with frontend repo URLs
- [ ] AC-5.2: `profile_extensions` includes `.ts` and `.tsx` file extensions
- [ ] AC-5.3: `processors` section maps file types to extractor adapters
- [ ] AC-5.4: `file_globs` pattern support exists or `profile_extensions` suffix matching covers TypeScript
- [ ] AC-5.5: Config validates against schema and fails fast on invalid entries

### US-6: Generate ChatML JSONL Training Data
**As a** ML engineer
**I want to** export extracted frontend knowledge as ChatML JSONL
**So that** I can fine-tune models on HomeAssistant/Lit component behavior

**Acceptance Criteria:**
- [ ] AC-6.1: Export format is valid JSONL with one record per line
- [ ] AC-6.2: Each record follows ChatML format: `{ messages: [{role, content}] }`
- [ ] AC-6.3: System message contains component metadata schema context
- [ ] AC-6.4: User message contains extraction prompt with source code snippet
- [ ] AC-6.5: Assistant message contains structured JSON output matching schema
- [ ] AC-6.6: Output passes JSON validation and Axolotl training compatibility check

### US-7: Integrate Taxonomy Prompts for Frontend Metadata
**As a** ML engineer
**I want to** use taxonomy prompts that extract component metadata into structured schema
**So that** extracted data is consistent and machine-readable

**Acceptance Criteria:**
- [ ] AC-7.1: Taxonomy prompts cover all LitComponentExtractor output fields
- [ ] AC-7.2: Taxonomy prompts cover all I18nKeyExtractor output fields
- [ ] AC-7.3: Taxonomy prompts cover all ServiceCallExtractor output fields
- [ ] AC-7.4: Prompt includes examples for each extraction type
- [ ] AC-7.5: Prompts are generic (not HomeAssistant-specific) to support other Lit frontends

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | **TypeScriptAdapter** base class implementing ExtractorAdapter protocol | High | Adapter parses .ts/.tsx files, returns ParseResult with extracted modules |
| FR-2 | **LitComponentExtractor** plugin for TypeScriptAdapter | High | Extracts @customElement, @property, @state, observed attributes via AST |
| FR-3 | **I18nKeyExtractor** plugin for TypeScriptAdapter | High | Extracts localize() and hass.localize() keys via AST or regex fallback |
| FR-4 | **ServiceCallExtractor** plugin for TypeScriptAdapter | High | Extracts callService() domain, service, entity_id via AST |
| FR-5 | **TranslationJsonParser** standalone parser for JSON files | Medium | Flattens nested JSON to dot-path keys, handles ICU placeholders |
| FR-6 | **TypeScriptAdapterFactory** registry for adapter instantiation | Medium | Creates TypeScriptAdapter with configured extractors at runtime |
| FR-7 | **FrontendDiscoveryConfig** schema for stage-1 discovery | High | Validates static_repos, profile_extensions, processors, file_globs |
| FR-8 | **ChatMLExporter** for JSONL output generation | High | Produces valid ChatML JSONL with schema-compliant messages |
| FR-9 | **FrontendTaxonomyPrompts** system/user prompt templates | Medium | Covers all extractor output schemas with examples |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | **Parsing coverage** (regex fallback) | Key coverage | >= 85% for literal string patterns |
| NFR-2 | **AST parsing coverage** (tree-sitter/typescript-estree) | Key coverage | >= 95% including constant references |
| NFR-3 | **Parse latency** per file | Time | < 500ms for files <= 60KB |
| NFR-4 | **Output schema validation** | Pass rate | 100% of emitted records pass JSON schema |
| NFR-5 | **Generic architecture** | Framework coupling | Zero HomeAssistant-specific code in core adapters |

## Glossary

- **@customElement decorator**: TypeScript decorator that registers a Lit web component class with a custom tag name
- **LitElement**: Base class for Lit web components; components extend this via `extends LitElement`
- **callService pattern**: `hass.callService(domain, service, serviceData)` - HomeAssistant service invocation API
- **ICU message format**: International Components for Unicode - `{name}`, `{count, plural, =0 {Zero} other {#}}` placeholders
- **TypeScriptAdapter**: Base adapter class implementing ExtractorAdapter protocol for TypeScript/Lit files
- **LitComponentExtractor**: Plugin that extracts @customElement class metadata
- **I18nKeyExtractor**: Plugin that extracts i18n localize() call keys
- **ServiceCallExtractor**: Plugin that extracts hass.callService() invocations
- **ChatML JSONL**: JSON Lines format where each line is a valid JSON object; ChatML format uses `{messages: [{role, content}]}`
- **dot-path key**: i18n key format using dots as hierarchy separators (e.g., `ui.panel.lovelace.strategy.view.grid`)

## Out of Scope

- Python AST parsing (not applicable to TypeScript)
- Node.js runtime or npm package installation
- Webpack/bundler plugin parsing
- CSS style extraction
- Shadow DOM template parsing
- TypeScript type checker integration (parsing only, no semantic analysis)
- HomeAssistant-specific entity state machine logic

## Dependencies

- **tree-sitter** or **typescript-estree** for TypeScript AST parsing
- **Regex fallback** for cases where AST parsing fails or is unavailable
- **python-regex** for high-performance pattern matching
- **jsonschema** for output validation
- **PyYAML** for config parsing

## Unresolved Questions

1. **Tree-sitter vs typescript-estree**: Which AST library to use for primary parsing? Tree-sitter is more robust but requires native .so build. typescript-estree is pure Python but may miss edge cases.
2. **Constant reference resolution**: Should tag names defined as constants (`const TAG = 'ha-dialog'`) be resolved or marked as "unresolved"?
3. **Dynamic key handling**: Template literal keys (`localize(\`ui.card.${action}\`)`) only yield prefix. Is prefix-only acceptable for training data?
4. **Per-component vs per-file bundling**: Should output bundles be emitted per-component, per-file, or per-module?
5. **Regex fallback threshold**: Regex achieves 85% coverage. Is this acceptable for v1, or should AST be mandatory?

## Success Criteria

1. **Parsers execute** on a sample of 100 TypeScript/TSX files and produce structured ParseResult output without crashes
2. **Schema validation passes** for 100% of output records against defined JSON schemas
3. **LitComponentExtractor** successfully detects 1,300+ @customElement registrations (validated against known 1,382 count)
4. **ServiceCallExtractor** extracts domain/service pairs matching the 332 known service call references
5. **I18nKeyExtractor** extracts keys covering 1,200+ of the 1,253 static localize() calls (>= 95% coverage)
6. **ChatML JSONL output** is valid JSONL with correct ChatML message structure and passes Axolotl training compatibility check
7. **Discovery config** loads without validation errors and triggers correct adapter routing for .ts/.tsx files
8. **Generic architecture** verified by successfully parsing a non-HomeAssistant Lit component file without code changes

## Next Steps

1. Select AST parsing strategy (tree-sitter or typescript-estree) based on deployment constraints
2. Implement TypeScriptAdapter base class following ExtractorAdapter protocol
3. Implement LitComponentExtractor, I18nKeyExtractor, ServiceCallExtractor as pluggable plugins
4. Add frontend repo entry to homeassistant.yaml discovery config with .ts/.tsx profile_extensions
5. Generate ChatML JSONL exporter with schema validation
6. Create taxonomy prompts for all extractor output schemas
7. Run parsers on sample files and validate output against acceptance criteria
