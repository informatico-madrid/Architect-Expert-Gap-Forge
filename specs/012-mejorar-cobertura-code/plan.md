# Implementation Plan: Mejorar Cobertura de Código

**Branch**: `[012-mejorar-cobertura-code]` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-mejorar-cobertura-code/spec.md`

## Summary

Este plan implementa tests unitarios para todos los módulos de `src/` que tienen cobertura < 90%, con el objetivo de alcanzar >= 90% de cobertura en todos los archivos. Los tests utilizan mocks y fixtures para evitar dependencias externas y garantizar ejecutabilidad sin red.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: pytest, pytest-cov, tiktoken, pydantic  
**Storage**: archivos JSONL en sistema de archivos local  
**Testing**: pytest con cobertura pytest-cov  
**Target Platform**: Linux server (Home Assistant container)  
**Project Type**: Pipeline de generación de datasets para entrenamiento de LLMs  
**Performance Goals**: Tests deben ejecutarse en < 30 segundos sin dependencias de red  
**Constraints**: >= 90% cobertura de código, mocks para servicios externos, fixtures en tests/fixtures/  
**Scale/Scope**: ~15 archivos fuente que necesitan tests adicionales

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance Verification

- [x] **Testing & Coverage**: CI espera >= 90% cobertura para módulos `src/audit`, `src/utils`
- [x] **Unit tests required**: Se crearán tests unitarios con pytest y fixtures tipados
- [x] **Strict typing**: Los fixtures usarán dataclasses y pydantic models
- [x] **No import-time side-effects**: Los tests no tendrán side-effects en import
- [x] **Logging**: Se usará `logger = logging.getLogger(__name__)` con lazy formatting
- [x] **Header policy**: Los nuevos archivos tendrán headers AEGF
- [x] **No silent failures**: Los tests verificarán excepciones explícitas
- [x] **No pragma: no cover**: Se evitará excepto para boilerplate unavoidable

**GATE PASSED**: No violaciones de constitution encontradas.

## Project Structure

### Documentation (this feature)

```text
specs/012-mejorar-cobertura-code/
├── plan.md              # This file
├── spec.md              # Feature specification
├── checklists/
│   └── requirements.md  # Specification quality checklist
├── research.md          # Phase 0 output (if needed)
├── data-model.md        # Phase 1 output (if needed)
├── quickstart.md        # Phase 1 output (if needed)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── audit/
│   ├── eval_bpb.py          <- tests: tests/test_eval_bpb.py
│   ├── calibration.py
│   ├── config.py
│   └── ...
├── curation/
│   ├── anchor_dataset_downloader.py  <- tests: tests/test_anchor_dataset_downloader.py
│   ├── dedup_and_validate.py         <- tests: tests/test_dedup_and_validate.py
│   ├── format_normalizer.py          <- tests: tests/test_format_normalizer.py
│   ├── dataset_mixer.py              <- tests: tests/test_dataset_mixer.py
│   └── ...
├── factory/
│   ├── agentic_teacher_client.py     <- tests: tests/test_agentic_teacher_client.py
│   ├── config.py                     <- tests: tests/test_factory_config.py
│   ├── hard_query_builder.py         <- tests: tests/test_hard_query_builder.py
│   ├── prompt_builder.py             <- tests: tests/test_prompt_builder_extended.py
│   └── ...
├── utils/
│   ├── cache_reset.py                <- tests: tests/test_cache_reset.py
│   ├── logging.py                    <- tests: tests/test_logging.py
│   └── extractors/
│       └── python_ast_adapter.py     <- tests: tests/test_python_ast_adapter.py
└── ...

tests/
├── fixtures/                        <- nuevos fixtures
│   ├── eval_bpb_examples.json
│   ├── anchor_dataset_examples.json
│   ├── format_normalizer_examples.json
│   ├── dedup_examples.json
│   └── ...
├── curation/
│   └── test_anchor_dataset_downloader.py
│   └── test_dedup_and_validate.py
│   └── test_format_normalizer.py
│   └── test_dataset_mixer.py
├── factory/
│   ├── test_agentic_teacher_client.py
│   ├── test_factory_config.py
│   ├── test_hard_query_builder.py
│   └── test_prompt_builder_extended.py
├── audit/
│   └── test_eval_bpb.py
├── utils/
│   ├── test_cache_reset.py
│   ├── test_logging.py
│   └── test_python_ast_adapter.py
└── ...
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | Este es un proyecto de mantenimiento de tests, no requiere arquitectura compleja | El proyecto ya tiene una arquitectura establecida que se sigue |

## Test Coverage Targets

### Módulos con 0% cobertura (prioridad máxima)
1. `src/audit/eval_bpb.py` - 1133 stmts, 648 missing
2. `src/utils/logging.py` - 16 stmts, 16 missing
3. `src/utils/cache_reset.py` - 117 stmts, 117 missing

### Módulos con baja cobertura (< 50%)
4. `src/curation/anchor_dataset_downloader.py` - 20%
5. `src/curation/dedup_and_validate.py` - 40%
6. `src/curation/dataset_mixer.py` - 34%
7. `src/curation/format_normalizer.py` - 54%

### Módulos con cobertura media (70-85%)
8. `src/factory/agentic_teacher_client.py` - 78%
9. `src/factory/config.py` - 69%
10. `src/factory/hard_query_builder.py` - 74%
11. `src/utils/extractors/python_ast_adapter.py` - 71%
12. `src/factory/prompt_builder.py` - 86%

## Implementation Phases

### Phase 0: Research (if needed)
- Investigar patrones de fixtures existentes en el proyecto
- Identificar servicios externos que necesitan mockear

### Phase 1: Design & Contracts
- Definir estructura de fixtures para cada módulo
- Documentar contratos de mocks para servicios externos

### Phase 2: Implementation
- Crear fixtures en `tests/fixtures/`
- Escribir tests unitarios para cada módulo
- Ejecutar `make coverage` para verificar >= 90%

## Next Steps

Ejecutar `/speckit.tasks` para generar tasks.md con las tareas de implementación detalladas.
