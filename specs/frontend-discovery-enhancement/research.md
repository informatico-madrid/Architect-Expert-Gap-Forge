# Research: frontend-discovery-enhancement

## Executive Summary

The data factory needs generic frontend parsing capabilities to ingest HomeAssistant frontend files (TypeScript/Lit components, i18n JSON, service calls). Current discovery system lacks TypeScript/JavaScript adapter, i18n extraction, and service call parsing. Solution: build a new `TypeScriptAdapter` following the existing `ExtractorAdapter` protocol, with specialized extractors for Lit components (`LitExtensionAdapter`), i18n keys (`I18nExtensionAdapter`), and service calls (`ServiceCallsExtensionAdapter`).

**Key findings**: (1) 1,382 `@customElement` registrations in HA frontend are extractable via AST; (2) `file_globs` is NOT implemented—only `profile_extensions` (suffix-based); (3) service calls follow `hass.callService(domain, service, serviceData)` pattern with 332 references; (4) i18n uses `localize('key')` and `hass.localize()` with nested JSON; (5) regex fallback achieves ~85% coverage, tree-sitter is most robust.

---

## External Research

### Lit/TypeScript Component Parsing

**@customElement decorator detection**:
```
ClassDeclaration → decorators[0].expression.CallExpression
  callee.name === 'customElement'
  arguments[0].value === 'element-tag'
```

**Extractable metadata**: tag name, class name, @property (type, default, attribute, reflect, state), @state, observed attributes, i18n keys, service calls.

**Parsing library ranking**: tree-sitter (most robust, requires .so build) > typescript-estree > @babel/parser > regex fallback.

**Challenges**: constant references for tag names, aliased imports (`import { customElement as ce }`), namespace imports.

### i18n Extraction Patterns

**Key patterns found**:
- `localize('ui.xxx')` — custom-cards pattern
- `hass.localize("ui.xxx")` — HomeAssistant built-in
- `localize('state.xxx')` — state translation
- `localize('component.xxx')` — component translation
- `setupCustomlocalize()` — custom wrapper pattern

**Dynamic keys**: ~20% use template literals (e.g., `` localize(`ui.card.${action}`) ``) — only prefix extractable.

**Translation JSON structure**: deeply nested JSON with dot-path keys (e.g., `mfa_setup.totp.step.init.title`). Leaf detection via string-only values.

**ICU format**: supported via `IntlMessageFormat` — syntax: `{name}`, `{count, plural, =0 {Zero} other {#}}`.

### Service Call Patterns

**Pattern**: `hass.callService(domain, service, serviceData)`
- Domain: always string literal
- Service: always string literal
- entity_id: in serviceData object

**Variable prefixes observed**: `this.hass` (TS), `context._hass` (Bubble-Card), `hass` (function param).

**Domains identified** (15+): cover, light, climate, media_player, fan, lock, vacuum, humidifier, update, input_number, input_select, select, number, alarm_control_panel.

**AST structure**: `CallExpression` with `callee.property.name === 'callService'`, args: [domain, service, serviceData?, target?]

---

## Codebase Analysis

### Existing Discovery System

**Config files**:
| File | Purpose |
|------|---------|
| `configs/homeassistant.yaml` | Main HA discovery config |
| `configs/stage_1_discovery/discovery.yaml.example` | Example agnostic config |
| `configs/stage_1_discovery/master_docs_map.yaml` | Profile-to-doc mapping |
| `configs/stage_1_discovery/examples/homeassistant.yaml` | HA profile example |
| `configs/stage_1_discovery/examples/*.yaml` | Other profile examples |

**Key classes**:
- `RepoIngestor` — discovers/clones repos
- `RepoProcessor` — bundles and emits parsed modules
- `ModuleDiscoveryStrategy` — manifest, init, directory, manual_mapping

**ExtractorAdapter Protocol**:
```python
def parse_file(file_path: Path) -> ParseResult
def extract_dependencies(file_path: Path) -> List[Dependency]
```

**Registered adapters**: `python`, `python-ast`, `homeassistant` (PythonAstAdapter), `php_legacy` (PhpLegacyAdapter)

### Critical Gap: No TypeScript/JavaScript Adapter

- No TS/JS parser registered
- No glob pattern support (only `profile_extensions` suffix matching)
- No LitElement-specific extraction
- No i18n key extraction
- No service call extraction

### Frontend Size Limits
- Frontend: 60 KB max (`MAX_SIZE_FRONTEND = 60_000`)
- Backend repos: `{"core", "integration", "alarmo"}`

---

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| Lit component parsing | **High** | 1,382 elements detectable via @customElement |
| Service call extraction | **High** | 332 refs, consistent `callService` pattern |
| i18n key extraction | **Medium** | ~85% via regex, dynamic keys need heuristics |
| TypeScript AST parsing | **Medium** | No Python TS parser—need tree-sitter or Node.js bridge |
| Config changes | **Low** | YAML additions only |
| Generic architecture | **High** | Follow existing ExtractorAdapter protocol |

**Effort**: M/L | **Risk**: Medium (TS AST parsing is the wild card) | **Feasibility**: High

---

## Recommendations for Requirements

### 1. Parser Architecture
- Build `TypeScriptExtensionAdapter` following existing `ExtractorAdapter` protocol
- Support tree-sitter for robust AST, with regex fallback for simple patterns
- `profile_extensions` already supports `.ts` and `.tsx`

### 2. Three Core Extractors
- **LitComponentExtractor**: @customElement, @property, @state, observed attributes
- **I18nKeyExtractor**: localize() calls, hass.localize(), JSON key files
- **ServiceCallExtractor**: callService() pattern, domain/service/entity_id

### 3. Discovery Config Updates
- Add `static_repos` entry for homeassistant/frontend
- Ensure `.ts` and `.tsx` in `profile_extensions`
- Add `processors` section referencing new extractors

### 4. Taxonomy Updates
- Add frontend-specific system/user prompts for metadata extraction
- Component schema: tag, class, file_path, props, events, service_calls, i18n_keys

### 5. Export Format
- ChatML JSONL for Axolotl training compatibility
- Per-component entries with system context + user extraction prompt

---

## Open Questions

1. Should constant references for tag names be resolved or marked "unresolved"?
2. Should `.ts` vs `.tsx` be handled differently?
3. What granularity for emitted bundles (per-component, per-file, per-module)?
4. Regex fallback only achieves 85% — is that acceptable for v1?
5. Should we use Node.js (esprima) bridge or pure Python (tree-sitter)?

---

## Sources

- `.research-lit-parsing.md` — Lit/TS parsing research
- `.research-i18n-patterns.md` — i18n extraction patterns
- `.research-service-calls.md` — Service call patterns
- `.research-codebase.md` — Existing discovery system analysis
