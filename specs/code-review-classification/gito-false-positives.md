# Gito False Positives - Contexto para Code Review

## Definición

Un **FALSE_POSITIVE** en el contexto de gito review es un issue reportado que NO requiere acción porque:

1. **Es intencional según la spec**: El código sigue un patrón requerido por la spec actual
2. **Es pre-existente**: El issue existe en main y no fue introducido por esta rama
3. **Es un fixture de test**: Archivos en `tests/fixtures/` son excluidos de lint
4. **Es diseño intencional**: Patrones como frozen dataclasses, global loaders, etc.
5. **Es Meta/documentation**: Issues de legibilidad en archivos .md

## Ejemplos de FALSE_POSITIVEs

### 1. Test Fixtures Intencionales
```python
# tests/fixtures/ - ruff excluye estos directorios
# No reportar issues en archivos de fixtures
```

### 2. Frozen Dataclasses con __setattr__
```python
# Es intencional para objetos inmutables
# No usar object.__setattr__ con self es UNERROR en frozen dataclasses
```

### 3. sys.path.insert() para Imports
```python
# Es intencional para estructura de proyecto
# Mover imports al top rompería la funcionalidad
```

### 4. Hardcoded Keys en Main (que esta rama remueve)
```python
# Si main tiene "sk-master-bunker-2026" y esta rama lo REMUEVE
# El diff REMOVIENDO es CORRECTO, no un bug
```

### 5. PEP 508 Violations en requirements.txt
```toml
# Ruff no puede parsear algunas sintaxis de pip
# Son false positives de ruff, no bugs reales
```

### 6. Build Artifacts
```bash
# build/lib/ - archivos regenerados no son bugs
```

### 7. Spec Documentation Updates
```markdown
# changes a .md files en specs/ son intencionales
```

## Cómo Usar Este Documento

Cuando gito reporta un issue:
1. Consultar este documento para ver si es un FALSE_POSITIVE conocido
2. Si es intentional según la spec actual → FALSE_POSITIVE
3. Si el issue existe en main → FALSE_POSITIVE (pre-existente)
4. Solo clasificar como REAL si es un bug genuino

## Issues que SI son REAL

- Bugs en código de producción (no tests)
- Errores de sintaxis
- security vulnerabilities introducidas por esta rama
- Assertions que masking failures
- Test setup que no match con implementation

## Issues que NO son REAL (FALSE_POSITIVES)

- Issues en `tests/fixtures/`
- Issues en `build/lib/`
- Issues en archivos .md de specs
- Issues de diseño intencional documentados arriba
- PEP 508 que ruff no puede parsear
- sys.path.insert() patterns
- Frozen dataclass __setattr__ patterns