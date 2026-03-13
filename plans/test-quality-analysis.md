# Análisis de Calidad de Tests en Ralph Loop

## Resumen Ejecutivo

El agente de Ralph Loop NO está siendo óptimo al crear tests debido a que los prompts actuales **no restringen suficientemente** el proceso de creación de tests. Se necesita mejorar la guía en los prompts para lograr cobertura alta con tests eficientes y ligeros.

---

## Estado Actual

### Tests Existentes
- **Total**: ~13,630 líneas de código en tests/
- **Archivos más grandes**: 
  - `test_model_evaluator_integration_paths.py` (1,456 líneas)
  - `test_nemo_curator_suite.py` (845 líneas)
  - `test_production_v11.py` (736 líneas)

### Requisitos de Cobertura (Constitution)
- Mínimo 90% coverage para `src/audit`, `src/utils`, `src/factory`, `src/curation`
- `# pragma: no cover` PROHIBIDO excepto para boilerplate inevitable

---

## Problemas Identificados

### 1. ❌ Sin Plantilla de Test Estándar

Los prompts NO incluyen una plantilla estándar para crear tests. Cada test se crea de manera ad-hoc.

**Impacto**: Inconsistencia en estructura, tests difíciles de mantener.

### 2. ❌ Sin Guía de Mocks Ligeros

El proyecto tiene fixtures en `tests/conftest.py` pero el agente NO sabe cuándo ni cómo usarlos:

```python
# Ejemplo de fixture disponible pero infrautilizado:
@pytest.fixture
def mock_inference_client() -> MagicMock:
    """A MagicMock that conforms to BaseInferenceClient's interface."""
    client = MagicMock()
    client.generate.return_value = '{"result": "ok"}'
    client.generate_with_retry.return_value = '{"result": "ok"}'
    return client
```

**Problema**: El agente no sabe que existe este fixture.

### 3. ❌ Sin Patrón Arrange-Act-Assert

No hay guía sobre cómo estructurar los tests:
- **Arrange**: Preparar datos y mocks
- **Act**: Ejecutar la función bajo test
- **Assert**: Verificar resultados

### 4. ❌ Sin Categorización de Tests

Los prompts no distinguen entre:
- **Unit tests**: Tests puros sin I/O ni red
- **Integration tests**: Tests que cruzan límites de módulos
- **Contract tests**: Tests de interfaces/APIs

### 5. ❌ Sin Cobertura de Edge Cases

El agente no sabe cómo generar tests para:
- Casos edge/nedge
- Errores y excepciones
- Estados de error

### 6. ❌ Sin Requisitos de Nombre

No hay convención de nombres para tests:
- `test_[module]_[function]_[scenario]`
- `test_[class]_[method]_[expected_behavior]`

---

## Prompts Actuales que Mencionan Tests

### speckit.implement.agent.md (líneas 114-119)
```
- **Tests before code**: If you need to write tests for contracts, entities, and integration scenarios
- **Polish and validation**: Unit tests, performance optimization, documentation
```

### Constitution.md (línea 43-44)
```
- Unit tests and integration tests are required for new modules. Use pytest and typed fixtures in tests/.
- Coverage requirements: CI expects >= 90% coverage
```

### AEGF.agent.md (línea 43-44)
```
- **Target:** Minimum coverage 90%.
- **Coverage Integrity:** The use of # pragma: no cover is STRICTLY PROHIBITED
```

---

## Recomendaciones de Mejora

### 1. 📝 Crear Plantilla de Test Estándar

Agregar al prompt del agente:

```
## Test Pattern Template

Use this exact structure for ALL tests:

```python
class Test[ModuleName]:
    """Tests for src/module.py"""

    @pytest.fixture
    def setup_(self) -> SomeType:
        """Arrange: Create test fixtures and mocks."""
        return SomeType()

    def test_[function]_[scenario]_[expected](self, setup_):
        \"\"\"Test that [description of what is tested].\"\"\"
        # Arrange
        input_data = ...

        # Act
        result = function_under_test(input_data)

        # Assert
        assert result == expected
```

### 2. 🎯 Guía de Mocks

```
## Mocking Guidelines

Use these patterns in order of preference:

1. **Unit-level mocks**: Use `@pytest.fixture` in conftest.py
2. **Function-level mocks**: Use `unittest.mock.patch` decorator
3. **Integration mocks**: Use provided fixtures like `mock_inference_client`

DO NOT:
- Mock internal implementation details
- Mock data structures (use real objects)
- Create complex mock chains (>3 levels)

DO:
- Mock ONLY external dependencies (APIs, file I/O, network)
- Use type hints in fixtures
- Keep mocks as simple as possible
```

### 3. 📊 Categorización de Tests

```
## Test Categories

Add this comment at the top of each test file:

```python
# UNIT TESTS: Pure functions, no I/O, no network
# Location: tests/unit/
# Example: tests/unit/test_math_helpers.py

# INTEGRATION TESTS: Cross-module, real I/O allowed
# Location: tests/integration/
# Example: tests/integration/test_pipeline.py

# CONTRACT TESTS: API/interface validation
# Location: tests/contract/
# Example: tests/contract/test_api_client.py
```

### 4. 🔄 Patrón Arrange-Act-Assert

```
## Test Structure - MANDATORY

Every test MUST follow this structure:

def test_something(self):
    # SECTION 1: ARRANGE (setup)
    # - Create test data
    # - Set up mocks
    # - Prepare inputs
    # NO code execution here

    # SECTION 2: ACT (execute)
    # - Call the function under test
    # - ONLY ONE line of code
    actual = function(input)

    # SECTION 3: ASSERT (verify)
    # - Assertions about the result
    # - Use descriptive assert messages
    assert actual == expected, f"Expected {expected}, got {actual}"
```

### 5. 🎲 Edge Cases Checklist

```
## Edge Case Testing - REQUIRED

For every function, test these edge cases:

1. Empty inputs: [], {}, "", None
2. Single element: [x], {x: y}
3. Maximum values: int max, float max
4. Minimum values: int min, 0, negative
5. Type errors: wrong input types
6. Exception paths: try/except branches
7. Boundary conditions: -1, 0, 1, max-1, max

Example:
def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
```

### 6. 📋 Naming Convention

```
## Test Naming Convention - MANDATORY

Pattern: test_[module]_[function]_[scenario]_[expected]

Examples:
- test_parser_parse_valid_json_returns_dict()
- test_parser_parse_invalid_json_raises_ValueError()
- test_calculator_add_negative_numbers_returns_negative()
- test_calculator_add_empty_list_returns_zero()

Class naming:
Pattern: Test[ModuleName][Component]

Examples:
- TestParser
- TestCalculatorValidation
- TestAPIClientErrors
```

### 7. 📈 Coverage Strategy

```
## Coverage Strategy - HIGH PRIORITY

To achieve 90%+ coverage:

1. **Branch Coverage**: Test both True and False paths
   ```python
   if condition:  # needs test with True AND False
       do_something()
   else:
       do_other()
   ```

2. **Exception Coverage**: Every raise statement needs a test
   ```python
   with pytest.raises(SomeException):
       function_that_raises()
   ```

3. **Tuple Unpacking**: Each index needs a test
   ```python
   a, b = result  # test a, test b
   ```

4. **Early Returns**: Test each return path
   ```python
   if not valid:
       return None  # needs test
   return process()  # needs test
   ```

5. **Golden Path + Error Path**: Minimum 2 tests per function
   - Happy path (correct inputs)
   - Error path (invalid inputs)
```

### 8. 🔌 Fixture Reuse

```
## Fixture Reuse - ENCOURAGED

Add fixtures to tests/conftest.py following this pattern:

```python
@pytest.fixture
def sample_record() -> SampleRecord:
    """A single valid SampleRecord."""
    return SampleRecord(
        id="test-001",
        example_type="nominal",
        ...
    )

@pytest.fixture
def sample_records() -> List[SampleRecord]:
    """Multiple SampleRecords for batch testing."""
    return [make_sample(id=f"test-{i:03d}") for i in range(5)]
```

Then use in tests:
```python
def test_processor_handles_batch(sample_records):
    result = processor.process(sample_records)
    assert len(result) == 5
```

---

## Acción Recomendada: Crear TestPrompt.md

Crear un archivo de prompt específico para tests que el agente DEBE seguir:

```
.github/agents/speckit.test-prompt.md
```

Este archivo debería:
1. Incluir todas las plantillas arriba
2. Ser referenciado en el prompt de implementación
3. Incluir ejemplos de "good" vs "bad" tests

---

## Métricas Actuales

```bash
# Ejecutar para ver cobertura actual
pytest --cov=src --cov-report=term-missing tests/

# Ver tests por categoría
find tests -name "test_*.py" | wc -l  # Total tests
grep -r "def test_" tests/ | wc -l     # Total test functions
```

---

## Conclusión

El agente necesita:
1. **Plantillas explícitas** - No ad-hoc
2. **Fixtures predefinidos** - No reinventar mocks
3. **Estructura obligatoria** - AAA pattern
4. **Naming convention** - Consistencia
5. **Categorización** - Unit/Integration/Contract
6. **Estrategia de cobertura** - Cómo llegar a 90%

Sin estas restricciones, el agente crea tests inconsistentes, con baja cobertura, y difícil de mantener.
