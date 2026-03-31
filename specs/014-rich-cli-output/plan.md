# Implementation Plan: Rich Terminal Output para CLI

**Branch**: `014-rich-cli-output` | **Date**: 2026-03-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-rich-cli-output/spec.md`

## Summary

Implementar salida visual mejorada usando la biblioteca Rich en 23 scripts CLI del proyecto AEGF. El enfoque es agregar tablas, barras de progreso, paneles y formateo de errores a la CLI existente, manteniendo 100% de compatibilidad con tests existentes.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: rich (biblioteca de terminal enhancement)  
**Storage**: N/A - no hay cambios en almacenamiento  
**Testing**: pytest - verificar que todos los tests existentes sigan pasando  
**Target Platform**: Linux server, terminal interactivo  
**Project Type**: CLI tools / data processing pipeline  
**Performance Goals**: Output formateado no debe añadir más de 5% overhead  
**Constraints**: 
- Tests deben pasar 100%
- Output debe ser legible también cuando se pipea
- Backward compatibility con logging existente
**Scale/Scope**: 23 scripts CLI, ~50k LOC totales

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate 1: Testing & Coverage
- [x] Feature requires tests - **APPLICABLE**: La feature debe mantener 100% tests passing
- [x] Coverage requirements apply - **APPLICABLE**: Coverage >= 90% para src/audit, src/utils
- **Verdict**: PASS - La implementación de Rich no debe reducir coverage

### Gate 2: Coding Conventions
- [x] Strict typing required - **APPLICABLE**: Funciones que usan Rich deben mantener type hints
- [x] Immutability by default - **APPLICABLE**: No aplica directamente a output
- [x] No import-time side-effects - **APPLICABLE**: Import de Rich debe ser lazy
- [x] Logging pattern - **APPLICABLE**: Usar RichHandler para integrar con logging existente
- **Verdict**: PASS - Seguir convenciones existentes

### Gate 3: Header Policy
- [x] New source files need headers - **APPLICABLE**: Si se crean nuevos archivos
- **Verdict**: PASS - No se crean nuevos archivos, solo se modifican existentes

### Gate 4: DRY / No Silent Failures
- [x] DRY applies - **APPLICABLE**: Considerar módulo compartido para utilities de Rich
- [x] No silent failures - **APPLICABLE**: Errores deben mostrarse claramente
- **Verdict**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/014-rich-cli-output/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (if applicable)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── audit/
│   ├── cli.py           # MODIFICAR: agregar Rich output
│   └── calibration.py   # MODIFICAR: agregar Rich output
├── curation/
│   ├── curator_cli.py   # MODIFICAR: agregar Rich output
│   └── rewrite_cli.py  # MODIFICAR: agregar Rich output
├── discovery/
│   ├── ingestor.py      # MODIFICAR: agregar Rich output
│   └── processor_cli.py# MODIFICAR: agregar Rich output
├── factory/
│   ├── cli.py           # MODIFICAR: agregar Rich output
│   └── agentic_cli.py  # MODIFICAR: agregar Rich output
├── merger/              # 14 scripts - MODIFICAR: agregar Rich output
└── research/
    └── generate_batch_distilabel.py  # MODIFICAR: agregar Rich output
```

**Structure Decision**: Proyecto existente tipo CLI/data pipeline. No se crea nueva estructura, se modifican los archivos existentes en `src/` para agregar Rich.

## Phase 0: Research

No hay NEEDS CLARIFICATION en la especificación. La tecnología (Rich) está definida por la skill existente en `.roo/skills/rich-terminal-output/SKILL.md`.

### Research Findings

**Decision**: Usar biblioteca Rich de Python  
**Rationale**: 
- Skill existente definida en el proyecto
- Ampliamente mantenida y documentada
- Compatible con el requerimiento del usuario

**Alternatives considered**:
- `colorama`: Solo colores básicos, no tablas/progreso
- `click`: Framework de CLI, no para output
- `textual`: Framework de TUI, overkill para lo necesario

## Phase 1: Design & Contracts

### Data Model

No aplica - no hay nuevas entidades de datos. Esta feature es puramente de presentación/output.

### Interface Contracts

No aplica - no se exponen nuevas interfaces externas. Los scripts CLI existentes mantienen su interfaz de argumentos.

### Quickstart

Ver [quickstart.md](quickstart.md)

## Complexity Tracking

No hay violaciones que requieran justificación. La implementación es directa y no introduce nueva complejidad arquitectural.

---

## Próximos Pasos

1. Ejecutar `/speckit.tasks` para generar tareas de implementación
2. Implementar cambios script por script
3. Verificar que tests pasen después de cada cambio
