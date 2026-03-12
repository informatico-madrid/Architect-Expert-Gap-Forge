# Data Model: Refactorización de Módulos Monolíticos

**Phase**: 1 — Design  
**Date**: 2026-03-12

Este documento describe las entidades de datos y los contratos de tipo que conectan los submódulos resultantes de la refactorización. Es la referencia canónica para implementadores y revisores.

---

## Paquete `src/factory/` — Entidades

### `FragmentTypedDict` (existente, en `src/schemas/common.py`)

```
FragmentTypedDict
  name: str              — nombre del archivo/símbolo
  type: str              — "code" | "markdown" | "jinja" | "yaml"
  subtype: str           — dominio (ej. "homeassistant")
  skeleton: str          — firma/estructura del símbolo
  original: str          — código fuente completo
  context: str           — contexto de módulo/fichero
  virtual_filename: str  — ruta virtual para el prompt
```

### `TaxonomyState` *(nueva — reemplaza globales mutables)*

```
TaxonomyState
  prompts: dict[str, Any]          — plantillas cargadas desde YAML
  ha_error_templates: list[str]    — plantillas de errores HA
  jinja_variants: list[dict]       — variantes Jinja
  theory_taxonomy: dict[str, Any]  — taxonomía de fragmentos teóricos
```

> Reemplaza las variables globales `_TAX`, `HA_ERROR_TEMPLATES`, `_JINJA_VARIANTS`, `THEORY_TAXONOMY` del monolito.  
> Se pasa como argumento explícito; nunca se muta después de `load_taxonomy()`.

### `GeneratedSample`

```
GeneratedSample
  id: str                          — hash MD5 del fragmento
  conversation: list[dict]         — mensajes [{"role": ..., "content": ...}]
  metadata: dict[str, Any]         — tipo, subtipo, dificultad, flags
  filter_text: str                 — texto de filtrado para deduplicación
```

> Contrato de salida de `pipeline_runner.generate_sample_async()`.

### `CheckpointSet`

```
CheckpointSet = frozenset[str]     — conjunto de checkpoint keys ya procesados
```

> Retorno de `checkpoint.load_checkpoint()`.

### `LDIResult`

```
LDIResult
  is_valid: bool
  score: float
  reason: str
```

> Retorno de `ldi_validator.validate_ldi()`.

### `ExampleTypeAssignment`

```
ExampleTypeAssignment
  example_type: str                — "nominal" | "contrast" | "error_recovery"
  difficulty: str | None           — "easy" | "medium" | "hard" | None
```

> Retorno de `ldi_validator.assign_example_type()`.

---

## Paquete `src/audit/` — Entidades

### `SampleRecord` (existente)

```
SampleRecord
  id: str
  conversation: list[dict]
  metadata: dict[str, Any]
```

### `ExamRecord`

```
ExamRecord
  sample_id: str
  exam_question: str
  eval_criteria: list[str]
  target_patterns: list[str]
  reference_standards: str
  gap_analysis: str
```

> Contrato de salida de `exam_builder.generate_exam_question()`.  
> Contrato de entrada de `judge.llm_judge_score()` y `scorecard.compute_scorecard()`.

### `NormalizedJudgeResponse`

```
NormalizedJudgeResponse
  baseline: dict[str, float]       — puntuaciones por dimensión (modelo base)
  adapter: dict[str, float]        — puntuaciones por dimensión (modelo adaptado)
  reasoning: str                   — texto de razonamiento del judge
```

> Retorno de `judge.llm_judge_score()`.

### `ScoreCard`

```
ScoreCard
  sample_id: str
  dimensions: dict[str, float]
  composite_score: float
  delta_vs_baseline: float
  grade: str                       — "A" | "B" | "C" | "D" | "F"
  verdict: str                     — "PASS" | "MARGINAL" | "FAIL"
  notes: list[str]
```

> Retorno de `scorecard.compute_scorecard()`.

### `AuditReport` (existente, en `src/audit/schema.py`)

```
AuditReport
  run_id: str
  timestamp: str
  scorecards: list[ScoreCard]
  summary: dict[str, Any]
```

> Retorno de `report_writer.generate_report()`.

---

## Diagrama de flujo de datos

### `src/factory/` — pipeline de generación

```
[config.py]
    ↓ TaxonomyState, constantes
[prompt_builder.py]
    ↓ str (system_prompt), str (user_prompt)
[pipeline_runner.py]  ←←←  [fragment_extractor.py] → FragmentTypedDict
         ↓ FragmentTypedDict
    [ldi_validator.py] → LDIResult, ExampleTypeAssignment
         ↓ valid fragment
    [checkpoint.py] → CheckpointSet (read/write)
         ↓ GeneratedSample
    [cli.py] → AsyncFileWriter (via checkpoint)
```

### `src/audit/` — pipeline de evaluación

```
[config.py]
    ↓ CFG, singletons (PromptManager, InferenceRouter)
[gap_generator.py]
    ↓ str (gap_analysis)
[exam_builder.py]
    ↓ ExamRecord
[judge.py]
    ↓ NormalizedJudgeResponse
[scorecard.py]
    ↓ ScoreCard
[report_writer.py]
    ↓ AuditReport + archivos .md/.json
[cli.py]
```

---

## Reglas de validación inter-módulo

- `TaxonomyState` es inmutable después de `load_taxonomy()` — ningún submódulo puede mutar sus campos.
- `ExamRecord.exam_question` no puede ser vacío — `exam_builder` debe lanzar excepción explícita si el LLM devuelve respuesta vacía.
- `NormalizedJudgeResponse.baseline` y `.adapter` deben contener exactamente las mismas claves de dimensión — `scorecard` valida esta invariante al inicio de `compute_scorecard()`.
- `GeneratedSample.conversation` debe tener al menos un turno con `role="assistant"` — `pipeline_runner` valida antes de escribir.

---

## Estado de transición: tipos existentes vs. nuevos

| Tipo | Estado | Dónde definido | Acción |
|------|--------|---------------|--------|
| `FragmentTypedDict` | Existente | `src/schemas/common.py` | Sin cambios |
| `SampleRecord` | Existente | `src/audit/schema.py` | Sin cambios |
| `AuditReport` | Existente | `src/audit/schema.py` | Sin cambios |
| `TaxonomyState` | **Nuevo** | `src/factory/config.py` | Crear como `@dataclass(frozen=True)` |
| `GeneratedSample` | Existente (dict anónimo) | `production_v11.py` | Formalizar como `TypedDict` en `src/factory/config.py` |
| `LDIResult` | **Nuevo** | `src/factory/ldi_validator.py` | Crear como `@dataclass(frozen=True)` |
| `ExampleTypeAssignment` | **Nuevo** | `src/factory/ldi_validator.py` | Crear como `@dataclass(frozen=True)` |
| `ExamRecord` | Existente (dict anónimo) | `model_evaluator.py` | Formalizar como `TypedDict` en `src/audit/schema.py` |
| `NormalizedJudgeResponse` | Existente (dict anónimo) | `model_evaluator.py` | Formalizar como `TypedDict` en `src/audit/schema.py` |
| `ScoreCard` | Existente (dict anónimo) | `model_evaluator.py` | Formalizar como `@dataclass` en `src/audit/schema.py` |
