# Tests Documentation

This directory contains tests for the data factory ingestor, focusing on YAML configuration loading and validation.

## YAML Configuration Tests

### Overview

The YAML configuration tests ensure that:
1. YAML files are loaded correctly from disk
2. Configuration files are validated against the Pydantic schema
3. CLI integration works end-to-end
4. Specific bugs (like the `---` document separator issue) are detected

### Test Files

#### Integration Tests

| File | Purpose |
|------|---------|
| `tests/integration/test_ingestor_yaml_load.py` | Tests for loading YAML from disk and detecting bugs |
| `tests/integration/test_ingestor_cli.py` | CLI integration tests with Click runner |
| `tests/integration/test_ingestor_git_recovery.py` | Git recovery integration tests |

#### Unit Tests

| File | Purpose |
|------|---------|
| `tests/unit/test_ingestor_yaml_validation.py` | Pydantic validation tests |
| `tests/unit/test_ingestor_profile_filter.py` | Profile filter tests |
| `tests/unit/test_ingestor_git_fallback.py` | Git fallback tests |

### Test Fixtures

YAML configuration fixtures are located in `tests/fixtures/yaml_configs/`:

| File | Purpose |
|------|---------|
| `valid_config.yaml` | Valid configuration for testing successful loads |
| `invalid_syntax.yaml` | Malformed YAML for syntax error detection |
| `missing_category.yaml` | Config missing required `category` field |
| `invalid_mode.yaml` | Config with invalid enum value |
| `copyright_then_separator.yaml` | YAML with `---` after copyright header (bug detection) |

### Running Tests

```bash
# Run all YAML-related tests
PYTHONPATH=. pytest tests/integration/test_ingestor_yaml_load.py tests/integration/test_ingestor_cli.py tests/unit/test_ingestor_yaml_validation.py -v

# Run specific test class
PYTHONPATH=. pytest tests/integration/test_ingestor_yaml_load.py::TestYamlLoadFromDisk -v

# Run with coverage
PYTHONPATH=. pytest tests/ --cov=src.discovery.ingestor --cov-report=html
```

### Test Coverage

The YAML tests achieve:
- **90%+ coverage** on loader functions in `src/discovery/ingestor/`
- Detection of the YAML document separator bug (`---` after copyright)
- Validation of required fields in Pydantic models
- CLI integration coverage

### Key Test Patterns

1. **Load from disk**: Tests load actual YAML files from `tests/fixtures/yaml_configs/`
2. **Validation**: Pydantic model validation is tested with valid and invalid configs
3. **CLI**: Click runner tests validate the full CLI pipeline
4. **Edge cases**: Empty files, comment-only files, multi-document YAML
