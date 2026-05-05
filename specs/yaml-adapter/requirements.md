# Requirements: YAML/Jinja Adapter for Home Assistant

## User Story

**US-1:** As a data scientist, I want to extract patterns from Home Assistant YAML/blueprint files so that the AI can learn automation patterns, trigger configurations, and service call patterns.

**US-2:** As a developer, I want to extract Jinja template expressions so that the AI can learn templating patterns used in Home Assistant automations.

## Functional Requirements

### FR-1: YAML Adapter

Create a `YamlAdapter` class that:
- Parses `.yaml` and `.yml` files using a YAML parser (e.g., `pyyaml`)
- Extracts blueprint patterns: `blueprint`, `name`, `description`, `domain`, `input`
- Extracts trigger patterns: `trigger` with platforms (state, time_pattern, event, etc.)
- Extracts condition patterns: `condition` with conditions (state, time, numeric_state, etc.)
- Extracts action patterns: `action` with service calls, delays, actions
- Identifies Jinja expressions: `'!input'`, `{{ }}`, filters, tests
- Classifies file type: `blueprint`, `integration_config`, `automation`, `theme`

### FR-2: Jinja Adapter

Create a `JinjaAdapter` class that:
- Parses `.jinja` and `.jinja2` files
- Extracts template variables: `{{ variable }}`, `{% set variable %}`
- Extracts filters: `{{ value | filter }}`
- Extracts tests: `{{ value is test }}`
- Extracts loops: `{% for item in items %}`
- Extracts conditionals: `{% if condition %}`
- Identifies Home Assistant-specific expressions: `'!input'`, `states.entity_id`, `now`, `state_attr`

### FR-3: Output Schema

Both adapters should produce structured JSON output with:
- `file_path`: Source file path
- `file_type`: Type classification (blueprint, automation, etc.)
- `patterns`: List of detected patterns with locations
- `variables`: List of template variables
- `imports`: Any import statements (for blueprint dependencies)

### FR-4: Factory Integration

Register adapters in the factory:
- `.yaml` → `YamlAdapter`
- `.yml` → `YamlAdapter`
- `.jinja` → `JinjaAdapter`
- `.jinja2` → `JinjaAdapter`

## Acceptance Criteria

### AC-1: YAML Adapter

- [ ] AC-1.1: Parse YAML files without errors
- [ ] AC-1.2: Extract blueprint metadata (name, description, domain, input)
- [ ] AC-1.3: Extract trigger configurations with platform and conditions
- [ ] AC-1.4: Extract condition configurations with condition types
- [ ] AC-1.5: Extract action configurations with service calls
- [ ] AC-1.6: Identify Jinja expressions in YAML values

### AC-2: Jinja Adapter

- [ ] AC-2.1: Parse Jinja template files without errors
- [ ] AC-2.2: Extract template variables with line numbers
- [ ] AC-2.3: Extract filters with source variable
- [ ] AC-2.4: Extract conditionals with conditions
- [ ] AC-2.5: Extract loops with iterated items
- [ ] AC-2.6: Identify Home Assistant-specific expressions

### AC-3: Factory Integration

- [ ] AC-3.1: Factory returns YamlAdapter for `.yaml` and `.yml`
- [ ] AC-3.2: Factory returns JinjaAdapter for `.jinja` and `.jinja2`
- [ ] AC-3.3: Unknown extensions fall back to default adapter

## Non-Functional Requirements

### NFR-1: Performance
- Parse files up to 100KB in under 1 second
- Memory usage under 50MB for typical blueprint files

### NFR-2: Robustness
- Handle malformed YAML gracefully with error reporting
- Handle Jinja syntax errors with helpful messages
- Support UTF-8 encoding with error handling

### NFR-3: Compatibility
- Support YAML 1.1 and 1.2
- Support Jinja2 template syntax
- Work with Home Assistant blueprint format

## Technical Notes

### YAML Patterns

Blueprint structure:
```yaml
blueprint:
  name: "Example"
  description: "Example description"
  domain: automation
  input:
    climate_entity:
      name: "Climate"
      selector:
        entity:
          domain: climate
mode: single
trigger:
  - platform: time_pattern
    minutes: '0'
condition: []
action:
  - service: climate.set_hvac_mode
    data:
      entity_id: !input 'climate_entity'
      hvac_mode: heat
```

### Jinja Patterns

Template expression:
```jinja
{{ states('sensor.temperature') | float | round(1) }}
{% if is_state('switch.lights', 'on') %}
  Lights are on
{% endif %}
```

## Files to Create

1. `src/utils/extractors/yaml_adapter.py` - YamlAdapter class
2. `src/utils/extractors/jinja_adapter.py` - JinjaAdapter class
3. Update `src/utils/extractors/factory.py` - Register new adapters
4. Update `configs/stage_1_discovery/examples/homeassistant.yaml` - Add YAML/Jinja extensions
5. `tests/unit/test_yaml_adapter.py` - Unit tests
6. `tests/unit/test_jinja_adapter.py` - Unit tests
