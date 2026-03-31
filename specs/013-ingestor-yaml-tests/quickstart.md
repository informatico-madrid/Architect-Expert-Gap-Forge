# Quickstart: Tests de Carga YAML para Ingestor

## Objetivo

Agregar tests que validen la carga de archivos YAML de configuración desde disco, detectando errores como el bug del `---` después del copyright.

## Prerequisites

- Python 3.x instalado
- pytest instalado: `pip install pytest pyyaml pydantic`
- Acceso al repositorio con permisos de escritura en `tests/`

## Estructura de Tests a Crear

### 1. Tests de Carga YAML (tests/integration/test_ingestor_yaml_load.py)

```python
# Patrón de test básico
def test_load_valid_yaml_file():
    """Test que carga un archivo YAML válido desde disco."""
    config_path = "configs/stage_1_discovery/discovery.yaml.example"
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    config = DiscoveryConfig(**data)
    assert config.category is not None

def test_load_yaml_with_triple_dash_bug():
    """Test específico para detectar el bug del ---."""
    yaml_content = """# Copyright header
---
category: test_category
mode: static
static_repos:
  - repo1
"""
    # Este test debe fallar si el contenido antes de --- es ignorado
```

### 2. Tests de Validación (tests/unit/test_ingestor_yaml_validation.py)

```python
def test_missing_category_field():
    """Test que valida que falta category genera error."""
    with pytest.raises(ValidationError):
        DiscoveryConfig(model_dump={...})

def test_invalid_mode():
    """Test que valida modo inválido."""
    with pytest.raises(ValidationError):
        DiscoveryConfig(category="test", mode="invalid")
```

### 3. Tests de Integración CLI (tests/integration/test_ingestor_cli.py)

```python
def test_cli_loads_yaml_config():
    """Test del flujo CLI completo."""
    result = runner.invoke(cli, ["-c", "valid_config.yaml"])
    assert result.exit_code == 0
```

## Archivos de Configuración de Ejemplo

- `configs/stage_1_discovery/discovery.yaml.example`
- `examples/home_assistant_2026/configs/stage_1_discovery/discovery.yaml`

## Cómo Ejecutar los Tests

```bash
# Ejecutar todos los tests del ingestor
pytest tests/integration/test_ingestor*.py -v

# Ejecutar tests específicos de YAML
pytest tests/integration/test_ingestor_yaml_load.py -v

# Ejecutar con coverage
pytest tests/ --cov=src.discovery.ingestor --cov-report=html
```

## Expected Outcomes

- Tests que cargan archivos YAML reales desde disco
- Tests que detectan el bug del `---` después del copyright
- Tests que validan campos requeridos
- Cobertura >= 90% en funciones de carga de configuración
