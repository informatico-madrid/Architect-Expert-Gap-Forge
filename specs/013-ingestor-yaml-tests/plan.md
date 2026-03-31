# Implementation Plan: Tests de Carga YAML para Ingestor

**Branch**: `013-ingestor-yaml-tests` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-ingestor-yaml-tests/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Agregar tests de carga YAML desde disco para el ingestor que validen el flujo completo CLI → YAML → Pydantic. El problema actual es que los tests existentes solo crean objetos Pydantic directamente con datos hardcodeados, permitiendo que bugs como el `---` después del header de copyright pasen desapercibidos.

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: pytest, PyYAML, Pydantic  
**Storage**: N/A (feature de tests)  
**Testing**: pytest (según constitución)  
**Target Platform**: Linux server  
**Project Type**: CLI tool / library  
**Performance Goals**: Tests < 30 segundos por suite (SC-003)  
**Constraints**: Cobertura >= 90% para módulos rastreados (constitución)  
**Scale/Scope**: Módulos del ingestor en src/discovery/

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Unit tests required for new modules | ✅ PASS | Se crearán tests en tests/integration/ y tests/unit/ |
| Coverage >= 90% for tracked modules | ✅ PASS | Objetivo: >= 90% en funciones de carga |
| Strict typing | ✅ PASS | Tests usarán tipos de Python |
| Pydantic models | ✅ PASS | DiscoveryConfig es Pydantic |
| No silent failures | ✅ PASS | Tests validarán errores explícitos |

## Project Structure

### Documentation (this feature)

```text
specs/013-ingestor-yaml-tests/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md # Quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── discovery/
    ├── ingestor.py      # Contains DiscoveryConfig and YAML loading functions
    └── processor_cli.py # CLI that loads YAML

tests/
├── integration/
│   ├── test_ingestor_git_recovery.py   # Existing
│   └── test_ingestor_yaml_load.py      # NEW - Tests loading YAML from disk
└── unit/
    ├── test_ingestor_profile_filter.py # Existing
    └── test_ingestor_yaml_validation.py # NEW - Tests validation
```

**Structure Decision**: Tests de integración en tests/integration/ (cargan archivos YAML reales), tests unitarios en tests/unit/ (usan mocking). Esta estructura sigue el patrón existente del proyecto.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Phase 0: Research - COMPLETED ✅

**Findings**: No se requieren clarificaciones adicionales. El problema está bien definido:
- Tests existentes solo crean objetos Pydantic directamente (líneas 40-86 en ingestor.py)
- No hay tests que usen yaml.safe_load() desde disco
- El bug del `---` después del copyright causa que yaml.safe_load() ignore el contenido antes del `---`

**Files to modify/create**:
- tests/integration/test_ingestor_yaml_load.py
- tests/unit/test_ingestor_yaml_validation.py

## Phase 1: Design & Contracts - COMPLETED ✅

### Data Model

Entities defined in [data-model.md](data-model.md):
- YAMLConfigFile - Archivo de configuración YAML
- DiscoveryConfig - Modelo Pydantic existente (src/discovery/ingestor.py:40)
- YAMLLoadResult - Resultado de carga YAML

### Contracts

Esta feature no tiene interfaces externas - es puramente tests. No se requiere directorio contracts/.

### Quickstart

Guía creada en [quickstart.md](quickstart.md) con:
- Estructura de tests a crear
- Patrones de código de ejemplo
- Comandos de ejecución

## Next Steps

Phase 2: Generar tasks.md usando `/speckit.tasks` para crear las tareas de implementación específicas.
