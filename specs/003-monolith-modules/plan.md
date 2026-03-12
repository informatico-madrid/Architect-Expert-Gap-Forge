# Implementation Plan: Refactorización de Módulos Monolíticos

**Branch**: `003-monolith-modules` | **Date**: 2026-03-12 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/003-monolith-modules/spec.md`

## Summary

Dividir los dos módulos monolíticos principales del proyecto (`src/factory/production_v11.py` con 2 565 LOC y `src/audit/model_evaluator.py` con 1 425 LOC) en submódulos de responsabilidad única, añadiendo contratos de tipo formalizados en cada frontera. La técnica es extracción sucesiva por responsabilidad con tests en verde después de cada paso. En una segunda fase (P2), se aplica el mismo patrón a cuatro archivos secundarios que también superan el umbral orientativo de 400 LOC.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: asyncio, openai (AsyncOpenAI), pydantic, pytest, tqdm, yaml  
**Storage**: Archivos JSONL en `data/synthetic/` y `data/audit/`; configs YAML en `configs/`  
**Testing**: pytest 9.0 + cobertura via pytest-cov; CI gate `make coverage` (≥ 90 %)  
**Target Platform**: Linux server (bunker, local GPU)  
**Project Type**: CLI + library interna  
**Performance Goals**: Sin SLA de latencia de importación. Sin cambio en throughput de generación.  
**Constraints**: Comportamiento observable idéntico (output JSONL bit-compatible). Cobertura ≥ 90 %. CI de cabeceras pasa.  
**Scale/Scope**: 2 archivos primarios (~4 000 LOC combinados) + 4 archivos secundarios (~5 300 LOC combinados)

## Constitution Check

*Pre-design gate — verificado 2026-03-12*

| § | Criterio | Estado |
|---|----------|--------|
| §III — Strict typing | Todos los submódulos nuevos tendrán funciones públicas anotadas | ✅ Planned |
| §III — Immutability | `TaxonomyState`, `LDIResult`, `ExampleTypeAssignment` serán frozen dataclasses | ✅ Planned |
| §III — No import-time side-effects | `load_dotenv()` y `CFG = _load_config()` se mueven a funciones lazy | ✅ Planned |
| §III — One logger per module | Cada nuevo `.py` tendrá `logger = logging.getLogger(__name__)` | ✅ Planned |
| §IV — SRP & module size | Objetivo de la feature: resolver esta violación | ✅ This feature |
| §V — Header policy | Todos los `.py` nuevos incluirán cabecera AEGF + SPDX | ✅ Planned |
| §II — Coverage ≥ 90 % | `src/audit` y `src/factory` deben mantener ≥ 90 % | ✅ Verified at baseline |
| §VII — No silent failures | Excepciones explícitas en contratos de tipo inter-módulo | ✅ Planned |

**No hay violaciones que requieran justificación.** La feature es en sí la remediación de la violación §IV existente.

## Project Structure

### Documentation (this feature)

```text
specs/003-monolith-modules/
├── plan.md              ← Este archivo
├── research.md          ← Decisiones de diseño y análisis de estructura
├── data-model.md        ← Entidades y contratos de tipo inter-módulo
├── quickstart.md        ← Guía de implementación paso a paso
└── tasks.md             ← Generado por /speckit.tasks (próximo paso)
```

### Source Code — Estructura resultante

```text
src/factory/
├── __init__.py                  # Re-export de API pública (actualizar)
├── config.py                    # NEW: constantes, TaxonomyState, GeneratedSample TypedDict
├── prompt_builder.py            # NEW: 25 funciones de construcción de prompts, detección legacy
├── fragment_extractor.py        # NEW: parsing de bundles, AST, get_fragments multi-formato
├── ldi_validator.py             # NEW: validate_ldi, assign_example_type, LDIResult, ExampleTypeAssignment
├── checkpoint.py                # NEW: make_checkpoint_key, load_checkpoint, AsyncFileWriter, ProgressTracker
├── pipeline_runner.py           # NEW: parse_raw_response, generate_sample_async, process_fragment, main_async
├── cli.py                       # NEW: configure_logger, parse_args, main()
├── production_v11.py            # DELETED al finalizar la fase
├── agentic_gen.py               # Existente — refactorización en Fase C (P2)
└── think_filter.py              # Existente — sin cambios

src/audit/
├── __init__.py                  # Re-export de API pública (actualizar)
├── config.py                    # NEW: CFG lazy, singletons PromptManager/InferenceRouter, DEFAULT_*
├── gap_generator.py             # NEW: generate_gap_analysis
├── exam_builder.py              # NEW: generate_exam_question, _build_domain_standards_section
├── judge.py                     # NEW: llm_judge_score, _extract_code_blocks, run_inference
├── scorecard.py                 # NEW: compute_scorecard, _composite, _grade_label, _verdict
├── report_writer.py             # NEW: generate_report
├── cli.py                       # NEW: 6 subcomandos, build_parser, main()
├── model_evaluator.py           # DELETED al finalizar la fase
├── inference.py                 # Existente — sin cambios
├── persistence.py               # Existente — sin cambios
├── prompt_manager.py            # Existente — sin cambios
├── sampling.py                  # Existente — sin cambios
└── schema.py                    # Existente — se añaden ExamRecord, NormalizedJudgeResponse, ScoreCard formalizados

src/schemas/
└── common.py                    # Existente — FragmentTypedDict sin cambios

tests/
├── test_production_v11*.py      # 16 archivos — actualizar imports en Fase A
├── test_model_evaluator*.py     # 7 archivos — actualizar imports en Fase B
└── (resto sin cambios)
```

**Structure Decision**: Single-project, extensión de paquetes existentes. No se crean sub-paquetes nuevos. Todos los submódulos viven en el mismo nivel que el monolito original para minimizar el diff y la complejidad de imports.

## Phase 0 — Research (Completo)

Ver [research.md](research.md) para el detalle completo. Resumen de decisiones clave:

1. **Descomposición `production_v11.py`**: 7 submódulos (`config` + 6 funcionales). Pipeline runner es el orquestador de dominio; CLI es hoja final.
2. **Descomposición `model_evaluator.py`**: 7 submódulos (`config` + 6 funcionales). Grafo de dependencias acíclico verificado.
3. **Side-effects en import-time**: Eliminados — `load_dotenv()` y `CFG = _load_config()` se hacen lazy; `_think_filter_apply` se extrae a función.
4. **Taxonomía global mutable**: Sustituida por `TaxonomyState` inmutable pasado como argumento.
5. **Compatibilidad de imports**: Sin período de transición; todos los consumidores se actualizan en el mismo PR.
6. **Umbral LOC**: Orientativo (400 LOC `wc -l`); el criterio real es SRP + testeabilidad.
7. **Baseline de tests verificado**: 83 passed (2026-03-12).

## Phase 1 — Design (Completo)

- **[data-model.md](data-model.md)**: Entidades por paquete, diagrama de flujo de datos, reglas de validación inter-módulo, tabla de estado de tipos.
- **contracts/**: No aplica — esta refactorización no expone nuevas APIs externas ni cambios de CLI observables. Los contratos son contratos internos de módulo documentados en data-model.md.
- **[quickstart.md](quickstart.md)**: Guía paso a paso para implementar cada fase, verificaciones, reglas de cada fichero nuevo.

### Constitution Check post-design

Sin violaciones nuevas introducidas por el diseño. La formalización de tipos (`TaxonomyState`, `LDIResult`, `ExamRecord`, etc.) refuerza §III. La eliminación de side-effects de import-time refuerza §III. La estructura de paquetes plana evita complejidad innecesaria (§VIII YAGNI).

## Complexity Tracking

No hay violaciones a justificar. La feature reduce complejidad existente; no añade ninguna nueva.


## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
