# Research: Refactorización de Módulos Monolíticos

**Phase**: 0 — Research  
**Date**: 2026-03-12  
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## Decision 1: Mapa de descomposición `src/factory/production_v11.py` (2 565 LOC)

**Decision**: Extraer 6 submódulos + 1 módulo de constantes dentro de un nuevo paquete `src/factory/` (ya existente).

| Submódulo | Responsabilidad | Funciones/Clases | LOC estimado |
|-----------|----------------|------------------|-------------|
| `config.py` | Constantes globales, rutas por defecto, pesos de distribución | Constantes (líneas 68–98, 152–259, 325–339, 727–748) | ~80 |
| `prompt_builder.py` | Construcción de todos los mensajes sistema/usuario, carga de taxonomía, doc maestros, detección de patrones legacy, post-validación | 25 funciones (líneas 103–749) | ~350 |
| `fragment_extractor.py` | Parsing de bundles .txt, extracción AST, get_fragments multi-formato | 5 funciones (líneas 829–1 242) | ~220 |
| `ldi_validator.py` | Validación LDI, asignación de tipo de ejemplo (distribución 50/30/20) | 2 funciones (líneas 1 247–1 296) | ~60 |
| `checkpoint.py` | Claves de checkpoint, carga/persistencia de checkpoints, `AsyncFileWriter`, `ProgressTracker` | 2 funciones + 2 clases (líneas 1 301–1 457) | ~170 |
| `pipeline_runner.py` | Parse de respuesta LLM, loop async de generación, wrapper por fragmento, paso 1+2 orquestador async | 4 funciones (líneas 750–2 190) | ~400 |
| `cli.py` | `configure_logger`, `parse_args`, `main()` | 3 funciones (líneas 2 193–2 410) | ~220 |

**Rationale**: Partición por responsabilidad funcional observable directamente en el archivo. Cada unidad puede importarse y testearse sin el resto. El pipeline_runner actúa como orquestador de dominio (no como CLI).

**Alternatives considered**:  
- Dejar `ldi_validator` dentro de `pipeline_runner` → rechazado: la validación LDI es una responsabilidad de dominio independiente y ya está testada de forma aislada en `tests/test_production_v11.py`.  
- Fusionar `checkpoint` con `pipeline_runner` → rechazado: `AsyncFileWriter` y `ProgressTracker` son primitivos reutilizables que no deben depender de la lógica de generación.

---

## Decision 2: Mapa de descomposición `src/audit/model_evaluator.py` (1 425 LOC)

**Decision**: Extraer 6 submódulos + 1 módulo de utilidades dentro del paquete existente `src/audit/`.

| Submódulo | Responsabilidad | Funciones/Clases | LOC estimado |
|-----------|----------------|------------------|-------------|
| `config.py` | Constantes, paths por defecto, `_load_config()`, singletons lazy (PromptManager, InferenceRouter) | Líneas 81–262 | ~90 |
| `gap_generator.py` | Generación de análisis de gaps (domain standards, prompts) | `generate_gap_analysis()` (líneas 264–301) | ~80 |
| `exam_builder.py` | Construcción de preguntas de examen, sección de domain standards | `generate_exam_question()`, `_build_domain_standards_section()` (líneas 307–387) | ~120 |
| `judge.py` | Scoring LLM judge, extracción de bloques de código, inferencia | `llm_judge_score()`, `_extract_code_blocks()`, `run_inference()` (líneas 439–522) | ~130 |
| `scorecard.py` | Cómputo del scorecard compuesto, grade labels, veredicto | `compute_scorecard()`, `_composite()`, `_grade_label()`, `_verdict()` (líneas 525–720) | ~180 |
| `report_writer.py` | Generación y serialización del informe de evaluación | `generate_report()` (líneas 794–959) | ~180 |
| `cli.py` | 6 subcomandos CLI (`sample`, `generate-exam`, `baseline`, `adapter`, `score`, `full`), `build_parser()`, `main()` | Líneas 833–1 425 | ~420 |

**Rationale**: La cadena de datos es estrictamente lineal (`gap_generator` → `exam_builder` → `judge` → `scorecard` → `report_writer` → `cli`), por lo que no hay riesgo de ciclos. El grafo de dependencias es acíclico verificado.

**Alternatives considered**:  
- Fusionar `gap_generator` + `exam_builder` en un único `analysis.py` → rechazado: la separación permite testear la generación de exámenes sin necesitar el análisis completo de gaps.  
- Dejar `_grade_label` y `_verdict` en `report_writer` → rechazado: son funciones de clasificación de scores, semánticamente pertenecen al `scorecard`.

---

## Decision 3: Side-effects en tiempo de importación

**Decision**: Resolver antes de extraer submódulos.

| Archivo | Side-effect | Resolución |
|---------|-------------|-----------|
| `production_v11.py` | Dynamic import de `think_filter` (try/except en módulo) | Extraer a función lazy `_get_think_filter()` en `pipeline_runner.py`; no ejecutar en import-time |
| `production_v11.py` | Taxonomía mutable global (`_TAX`, etc.) mutada por `load_taxonomy()` | Pasar `taxonomy` como argumento explícito (dependency injection) en lugar de estado global |
| `model_evaluator.py` | `load_dotenv()` en módulo (línea 81) | Mover al bloque `if __name__ == "__main__"` o a `cli.py`; no ejecutar en import-time |
| `model_evaluator.py` | `CFG = _load_config()` en módulo (línea 123) | Hacer lazy: `CFG = None`; cargar en `_get_config()` → singleton |

**Rationale**: Eliminar side-effects de import-time es requisito de §III de la constitución y habilita tests sin I/O.

---

## Decision 4: Estrategia de compatibilidad (imports)

**Decision**: Sin período de transición. Todos los consumidores se actualizan en el mismo PR.

**Scope de consumidores a actualizar**:
- `tests/test_production_v11*.py` (16 archivos) → actualizar imports al nuevo sub-paquete
- `tests/test_model_evaluator*.py` (7 archivos) → actualizar imports al nuevo sub-paquete
- Ningún otro módulo en `src/` importa directamente estos dos archivos (verificado con `grep -r "production_v11\|model_evaluator" src/`)

**Rationale**: El conjunto de consumidores es conocido, acotado y en el mismo repositorio. No hay consumidores externos.

---

## Decision 5: Métrica de calidad de módulo

**Decision**: 400 LOC (medido con `wc -l`) es señal de alerta orientativa, no límite estricto. El criterio real es SRP + testeabilidad independiente. Un módulo puede superar 400 LOC si tiene justificación arquitectónica documentada.

**CI enforcement**: Añadir check de `wc -l` en `make lint` que emite un **warning** (no error) para archivos > 400 LOC en `src/`. Los archivos > 400 LOC requieren comentario `# ARCH-NOTE: <justificación>` en la cabecera.

---

## Decision 6: Estructura de paquetes

**Decision**: Los submódulos se crean dentro de los paquetes existentes (`src/factory/`, `src/audit/`). No se crean sub-paquetes nuevos (ej. `src/factory/core/`) para esta refactorización, ya que los paquetes actuales tienen el nivel de granularidad adecuado.

**`__init__.py` strategy**: Los `__init__.py` de los paquetes existentes se actualizan para re-exportar las APIs públicas (sólo las funciones/clases que eran públicas en el monolito original). No se usan re-exports de compatibilidad transitoria: todos los importadores se actualizan en el mismo PR.

---

## Decision 7: Cobertura de tests existentes antes de la refactorización

| Archivo | Tests existentes | Cobertura estimada |
|---------|-----------------|-------------------|
| `production_v11.py` | 16 archivos de test (~200+ test functions) | Alta — todos los submódulos propuestos tienen tests |
| `model_evaluator.py` | 7 archivos de test (~83 funciones en baseline) | Media-alta — CI pasa, cobertura OK en `src/audit` |

**Baseline verificado**: `83 passed` en `pytest tests/test_production_v11.py tests/test_model_evaluator.py` (2026-03-12).

**Required pre-work**: Ninguno. Cobertura existente es suficiente para detectar regresiones durante la refactorización.

---

## Riesgos identificados

| Riesgo | Probabilidad | Mitigation |
|--------|-------------|-----------|
| Tests que importan symbólos movidos se rompen al hacer el split | Alta | Actualizar todos los imports en el mismo PR bajo [VERIFY] gate |
| La taxonomía global mutable causa estado compartido entre tests | Media | Inyección de dependencias; cada test pasa su propia instancia de taxonomía |
| `load_dotenv()` en `model_evaluator` causa fallos en CI sin `.env` | Baja (CI ya pasa) | Mover a `cli.py`; documentado en Decision 3 |
| Archivos secundarios (backtracking_rewriter etc.) tienen interdependencias con los primarios | Baja | Son paquetes independientes; refactorizados en fase separada (US3, P2) |
