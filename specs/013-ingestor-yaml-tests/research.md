# Research: Tests de Carga YAML para Ingestor

## Decision: No se requieren clarificaciones adicionales

**Rationale**: La especificación no tiene marcadores [NEEDS CLARIFICATION]. El problema está bien definido:
- Tests existentes solo crean objetos Pydantic directamente
- No hay tests que carguen YAML desde disco
- El bug del `---` pasó desapercibido

**Alternatives evaluated**: N/A - el problema está claramente界定ado en el reporte de investigación del usuario.

---

## Technical Context Findings

### Current Code Structure

1. **DiscoveryConfig** (src/discovery/ingestor.py:40-86)
   - Modelo Pydantic con campo requerido `category` (línea 46)
   - Otros campos: mode, profile, profile_extensions, profile_ignored_paths, etc.
   - Validador que requiere static_repos para modo static o search_query para modo dynamic

2. **Carga YAML** (src/discovery/ingestor.py:563-567 y 594-598)
   - Dos funciones: `run()` y `main()` que cargan YAML
   - Usan `yaml.safe_load(f)` directamente
   - Crean `DiscoveryConfig(**config_data)` después de cargar

3. **Archivos de Configuración**
   - `configs/stage_1_discovery/discovery.yaml.example`
   - Ejemplos en `examples/home_assistant_2026/configs/stage_1_discovery/`

### Testing Approach

- Usar `pytest` existente en el proyecto
- Crear tests de integración que carguen archivos YAML reales
- Usar mocking con `unittest.mock.patch` para casos de error
- Archivos de test en `tests/integration/` y `tests/unit/`

### References

- Constitución del proyecto: `.specify/memory/constitution.md`
- Política de coverage: >= 90% para módulos rastreados
- Convenciones: strict typing, pydantic models, pytest
