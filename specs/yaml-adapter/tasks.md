# Tasks: YAML/Jinja Adapter Implementation

## Phase 1: Core Types and Base Classes

### 1.1 Create YAML parsing types and base classes [x]
- **Do**:
  1. Create `src/utils/extractors/extractors/yaml_base.py`
  2. Define `YamlPattern` dataclass with fields: `pattern_type`, `data`, `file_path`, `line_number`
  3. Define `BlueprintPattern`, `TriggerPattern`, `ConditionPattern`, `ActionPattern` subclasses
  4. Add output schemas as typed dicts for each pattern type
  5. Implement YAML parsing helper functions
- **Files**: `src/utils/extractors/extractors/yaml_base.py`
- **Done when**: Base types and patterns defined matching ExtractorAdapter pattern
- **Verify**: `python -c "from src.utils.extractors.extractors.yaml_base import YamlPattern; print('OK')"`
- **Commit**: `feat(adapter): add YAML parsing base types and patterns`
- _Requirements: FR-1, FR-3_

### 1.2 Create YamlAdapter [x]
- **Do**:
  1. Create `src/utils/extractors/yaml_adapter.py`
  2. Implement `YamlAdapter` class implementing `ExtractorAdapter` protocol
  3. Add `__init__` with yaml parser configuration
  4. Implement `parse_file(file_path: Path) -> ParseResult`
  5. Implement `extract_dependencies(file_path: Path) -> list[Dependency]`
  6. Extract blueprint patterns: name, description, domain, input
  7. Extract trigger patterns: platform, conditions, for
  8. Extract condition patterns: condition, entity_id, state
  9. Extract action patterns: service, data, entity_id
  10. Identify Jinja expressions: !input, {{ }}, filters, tests
- **Files**: `src/utils/extractors/yaml_adapter.py`
- **Done when**: YamlAdapter.parse_file returns ParseResult with YAML patterns
- **Verify**: `python -c "from src.utils.extractors.yaml_adapter import YamlAdapter; print('OK')"`
- **Commit**: `feat(adapter): add YamlAdapter for YAML/blueprint files`
- _Requirements: FR-1, FR-3, AC-1.1 to AC-1.6_

### 1.3 Create Jinja parsing types [x]
- **Do**:
  1. Create `src/utils/extractors/extractors/jinja_base.py`
  2. Define `JinjaToken` dataclass with fields: `token_type`, `data`, `file_path`, `line_number`
  3. Define `VariableToken`, `FilterToken`, `TestToken`, `LoopToken`, `ConditionalToken` subclasses
  4. Add output schemas for each token type
- **Files**: `src/utils/extractors/extractors/jinja_base.py`
- **Done when**: Base types defined for Jinja tokens
- **Verify**: `python -c "from src.utils.extractors.extractors.jinja_base import JinjaToken; print('OK')"`
- **Commit**: `feat(adapter): add Jinja parsing base types`
- _Requirements: FR-2_

### 1.4 Create JinjaAdapter [x]
- **Do**:
  1. Create `src/utils/extractors/jinja_adapter.py`
  2. Implement `JinjaAdapter` class implementing `ExtractorAdapter` protocol
  3. Add `__init__` with Jinja parser configuration
  4. Implement `parse_file(file_path: Path) -> ParseResult`
  5. Implement `extract_dependencies(file_path: Path) -> list[Dependency]`
  6. Extract template variables with line numbers
  7. Extract filters with source variable
  8. Extract conditionals with conditions
  9. Extract loops with iterated items
  10. Identify Home Assistant expressions: !input, states.entity_id, now, state_attr
- **Files**: `src/utils/extractors/jinja_adapter.py`
- **Done when**: JinjaAdapter.parse_file returns ParseResult with Jinja tokens
- **Verify**: `python -c "from src.utils.extractors.jinja_adapter import JinjaAdapter; print('OK')"`
- **Commit**: `feat(adapter): add JinjaAdapter for template files`
- _Requirements: FR-2, AC-2.1 to AC-2.6_

### 1.5 V1 [VERIFY] Quality checkpoint [x]
- **Do**: Run quality checks on Phase 1 files
- **Verify**: `python -m py_compile src/utils/extractors/extractors/yaml_base.py src/utils/extractors/yaml_adapter.py src/utils/extractors/extractors/jinja_base.py src/utils/extractors/jinja_adapter.py`
- **Done when**: All files compile without syntax errors
- **Commit**: `chore(adapter): pass quality checkpoint`

---

## Phase 2: Factory Integration

### 2.1 Register YAML adapter in factory [x]
- **Do**:
  1. Modify `src/utils/extractors/factory.py`
  2. Add `"yaml": "src.utils.extractors.yaml_adapter.YamlAdapter"` to `_ADAPTER_REGISTRY`
  3. Add `"yml": "src.utils.extractors.yaml_adapter.YamlAdapter"` alias
- **Files**: `src/utils/extractors/factory.py`
- **Done when**: Factory returns YamlAdapter for "yaml" and "yml" profiles
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('yaml'); print(type(a).__name__)"`
- **Commit**: `feat(factory): register YamlAdapter in adapter registry`
- _Requirements: FR-4_

### 2.2 Register Jinja adapter in factory [x]
- **Do**:
  1. Modify `src/utils/extractors/factory.py`
  2. Add `"jinja": "src.utils.extractors.jinja_adapter.JinjaAdapter"` to `_ADAPTER_REGISTRY`
  3. Add `"jinja2": "src.utils.extractors.jinja_adapter.JinjaAdapter"` alias
- **Files**: `src/utils/extractors/factory.py`
- **Done when**: Factory returns JinjaAdapter for "jinja" and "jinja2" profiles
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('jinja'); print(type(a).__name__)"`
- **Commit**: `feat(factory): register JinjaAdapter in adapter registry`
- _Requirements: FR-4_

### 2.3 V2 [VERIFY] Quality checkpoint [x]
- **Do**: Run quality checks and verify adapters load correctly
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; y = get_adapter('yaml'); j = get_adapter('jinja'); assert 'YamlAdapter' in type(y).__name__ and 'JinjaAdapter' in type(j).__name__"`
- **Done when**: Factory integration works
- **Commit**: `chore(factory): pass quality checkpoint`

---

## Phase 3: Configuration Updates

### 3.1 Update homeassistant.yaml config [x]
- **Do**:
  1. Modify `configs/stage_1_discovery/examples/homeassistant.yaml`
  2. Add `.yaml` and `.yml` to `extensions` list
  3. Add `.jinja` and `.jinja2` to `extensions` list
  4. Update documentation to reflect new extensions
- **Files**: `configs/stage_1_discovery/examples/homeassistant.yaml`
- **Done when**: homeassistant.yaml includes YAML/Jinja extensions
- **Verify**: `python -c "import yaml; cfg = yaml.safe_load(open('configs/stage_1_discovery/examples/homeassistant.yaml')); assert '.yaml' in cfg['extensions'] and '.jinja' in cfg['extensions']"`
- **Commit**: `feat(config): add YAML/Jinja extensions to homeassistant.yaml`
- _Requirements: AC-5.2_

### 3.2 V3 [VERIFY] Quality checkpoint [x]
- **Do**: Verify YAML configs load without errors
- **Verify**: `python -c "import yaml; yaml.safe_load(open('configs/stage_1_discovery/examples/homeassistant.yaml')); print('OK')"`
- **Done when**: All YAML configs are valid
- **Commit**: `chore(config): pass quality checkpoint`

---

## Phase 4: Unit Tests

### 4.1 Create test_yaml_adapter.py [x]
- **Do**:
  1. Create `tests/unit/extractors/test_yaml_adapter.py`
  2. Test parse_file returns ParseResult
  3. Test blueprint pattern extraction (name, description, domain, input)
  4. Test trigger pattern extraction (platform, conditions)
  5. Test condition pattern extraction (condition type, entity_id)
  6. Test action pattern extraction (service, data)
  7. Test Jinja expression detection (!input, {{ }})
  8. Create test fixtures for YAML samples
- **Files**: `tests/unit/extractors/test_yaml_adapter.py`, `tests/fixtures/yaml_samples/`
- **Done when**: All YAML adapter tests pass
- **Verify**: `python -m pytest tests/unit/extractors/test_yaml_adapter.py -v --tb=short`
- **Commit**: `test(yaml): add unit tests for YamlAdapter`
- _Requirements: AC-1.1 to AC-1.6_

### 4.2 Create test_jinja_adapter.py [x]
- **Do**:
  1. Create `tests/unit/extractors/test_jinja_adapter.py`
  2. Test parse_file returns ParseResult
  3. Test variable extraction with line numbers
  4. Test filter extraction with source variable
  5. Test conditional extraction with conditions
  6. Test loop extraction with iterated items
  7. Test Home Assistant expression detection
  8. Create test fixtures for Jinja samples
- **Files**: `tests/unit/extractors/test_jinja_adapter.py`, `tests/fixtures/jinja_samples/`
- **Done when**: All Jinja adapter tests pass
- **Verify**: `python -m pytest tests/unit/extractors/test_jinja_adapter.py -v --tb=short`
- **Commit**: `test(jinja): add unit tests for JinjaAdapter`
- _Requirements: AC-2.1 to AC-2.6_

### 4.3 Create test_factory_yaml_jinja.py [x]
- **Do**:
  1. Create `tests/unit/extractors/test_factory_yaml_jinja.py`
  2. Test get_adapter(".yaml") returns YamlAdapter
  3. Test get_adapter(".yml") returns YamlAdapter
  4. Test get_adapter(".jinja") returns JinjaAdapter
  5. Test get_adapter(".jinja2") returns JinjaAdapter
  6. Test unknown extensions fall back to default adapter
- **Files**: `tests/unit/extractors/test_factory_yaml_jinja.py`
- **Done when**: All factory tests pass
- **Verify**: `python -m pytest tests/unit/extractors/test_factory_yaml_jinja.py -v --tb=short`
- **Commit**: `test(factory): add unit tests for YAML/Jinja factory registration`
- _Requirements: AC-3.1 to AC-3.3_

### 4.4 V4 [VERIFY] Quality checkpoint: all unit tests [x]
- **Do**: Run all unit tests
- **Verify**: `python -m pytest tests/unit/extractors/test_yaml_adapter.py tests/unit/extractors/test_jinja_adapter.py tests/unit/extractors/test_factory_yaml_jinja.py -v --tb=short`
- **Done when**: All unit tests pass
- **Commit**: `chore(tests): pass unit test checkpoint`

---

## Phase 5: Integration and Validation

### 5.1 Integration test: YAML adapter end-to-end [x]
- **Do**:
  1. Create a sample YAML blueprint file
  2. Run YamlAdapter.parse_file() on it
  3. Verify all pattern types are extracted correctly
- **Files**: `tests/integration/test_yaml_adapter_e2e.py`
- **Done when**: Integration test passes
- **Verify**: `python -m pytest tests/integration/test_yaml_adapter_e2e.py -v --tb=short`
- **Commit**: `test(integration): add YamlAdapter e2e tests`
- _Requirements: Success Criteria 1, 2_

### 5.2 Integration test: Jinja adapter end-to-end [x]
- **Do**:
  1. Create a sample Jinja template file
  2. Run JinjaAdapter.parse_file() on it
  3. Verify all token types are extracted correctly
- **Files**: `tests/integration/test_jinja_adapter_e2e.py`
- **Done when**: Integration test passes
- **Verify**: `python -m pytest tests/integration/test_jinja_adapter_e2e.py -v --tb=short`
- **Commit**: `test(integration): add JinjaAdapter e2e tests`
- _Requirements: Success Criteria 1, 2_

### 5.3 Validation test: Process real Home Assistant blueprints [x]
- **Do**:
  1. Use existing blueprints from data/raw/homeassistant/
  2. Run YamlAdapter on real blueprint files
  3. Verify extraction works on production blueprints
- **Done when**: Real blueprint validation passes
- **Verify**: `python -c "from src.utils.extractors.factory import get_adapter; a = get_adapter('yaml'); result = a.parse_file(Path('path/to/blueprint.yaml')); print(f'Extracted {len(result.patterns)} patterns')"`
- **Commit**: `test(validation): process real Home Assistant blueprints`
- _Requirements: Success Criteria 3_

### 5.4 V5 [VERIFY] Final quality gate [x]
- **Do**: Run full test suite
- **Verify**: `python -m pytest tests/unit/extractors/ tests/integration/ -v --tb=short 2>&1 | tail -30`
- **Done when**: All tests pass, no regressions
- **Commit**: `chore(final): pass final quality gate`

---

## Phase 6: Documentation

### 6.1 Update README with YAML/Jinja support [x]
- **Do**:
  1. Update `README.md` in src/utils/extractors/
  2. Document YamlAdapter and JinjaAdapter
  3. Add examples of usage
- **Files**: `README.md`
- **Done when**: README updated with YAML/Jinja documentation
- **Verify**: `grep -q "YamlAdapter\|JinjaAdapter" README.md`
- **Commit**: `docs: update README with YAML/Jinja adapter documentation`

### 6.2 Create example usage script [x]
- **Do**:
  1. Create `examples/yaml_jinja_usage.py`
  2. Show how to use YamlAdapter and JinjaAdapter
  3. Include examples of output format
- **Files**: `examples/yaml_jinja_usage.py`
- **Done when**: Example script runs successfully
- **Verify**: `python examples/yaml_jinja_usage.py`
- **Commit**: `example(yaml): add usage examples for YAML/Jinja adapters`

---

## Notes

- Production TODOs: Implement tree-sitter parsing for YAML v2 (~95% coverage)
- Production TODOs: Add parallel processing for large blueprint collections
- Production TODOs: Add YAML schema validation against HA blueprint spec
