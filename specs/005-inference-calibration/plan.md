# Implementation Plan: Inference Calibration Suite (Stage 6)

**Branch**: `005-inference-calibration` | **Date**: 2026-03-15 | **Spec**: [spec.md](./spec.md)

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Sistema automatizado de optimización de parámetros de inferencia que utiliza el Professor Judge existente como función de recompensa. El sistema realiza un "Descending Coordinates Sweep" iterando a través de múltiples combinaciones de parámetros de muestreo (temperature, top_k, min_p, repetition_penalty), evalúa cada respuesta con el Judge, y genera archivos de salida optimizados (calibration_report.json y vllm_config.yaml) con los mejores parámetros encontrados. Incluye penalización por respuestas cortas (<200 palabras) para desalentar respuestas lazy.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: pytest, PyYAML, vLLM (OpenAI-compatible client), google-genai  
**Storage**: JSON files for progress checkpoint and calibration results  
**Testing**: pytest with fixtures in tests/  
**Target Platform**: Linux server with GPU  
**Project Type**: CLI tool / automation script  
**Performance Goals**: Sin límite de tiempo - ejecutar hasta completar (el servidor vLLM es el limitante principal)  
**Constraints**: Integración con infraestructura existente de Stage 5 (judge.py, inference.py) + reutilizar PromptManager existente  
**Scale/Scope**: 5-10 prompts de entrada, 54 combinaciones de parámetros por prompt (3×3×2×3)  

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| Strict typing | ✓ PASS | Usar dataclasses con slots y frozen=True |
| Immutability by default | ✓ PASS | Registros congelados, sin mutación |
| No import-time side effects | ✓ PASS | Módulos lazy-loaded |
| Logging convention | ✓ PASS | Un logger por módulo |
| Strategy + Router pattern | ✓ PASS | Reutilizar InferenceRouter existente |
| Prompt externalization | ✓ PASS | Templates en configs/stage_5_evaluation/ |
| Unit tests required | ✓ PASS | Crear tests para nuevos módulos |
| Coverage >= 90% | ✓ PASS | Agregar a coverage_check.json |

## Project Structure

### Documentation (this feature)

```text
specs/005-inference-calibration/
├── plan.md              # This file
├── research.md          # Phase 0 output (N/A - no unknowns)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - CLI tool)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── audit/
│   ├── calibration.py      # NEW: Main calibration engine
│   ├── calibration_schema.py # NEW: Dataclasses for calibration
│   └── cli.py             # EXTEND: Add calibration subcommand

tests/
├── test_audit_calibration.py  # NEW: Unit tests for calibration
└── fixtures/
    └── calibration_examples.json # NEW: Test prompts
```

**Structure Decision**: Extender el módulo `src/audit/` existente con nuevos archivos para mantener la cohesión con la infraestructura de Stage 5 (judge, inference, schema).

## Clarifications Incorporated

Las siguientes clarificaciones han sido integradas en este plan:
- **Rendimiento**: Sin límite específico - ejecutar hasta completar (el servidor vLLM es el limitante principal)
- **Formato de prompts**: Seguir la misma arquitectura y estructura existente del proyecto (reutilizar PromptManager)
- **Documentación**: Actualizar docs/METHODOLOGY.md con casos de uso Stage 6, actualizar README.md y otros docs relevantes

## Complexity Tracking

> **No violations detected.** La implementación reuse componentes existentes del Stage 5, sigue los patrones establecidos, y no introduce nuevos proyectos o arquitectura compleja.

---

## Phase 1: Design Details

### Data Model Extensions

Basándose en las entidades definidas en la especificación:

**SamplingProfile** (nuevo dataclass):
```python
@dataclass(slots=True, frozen=True)
class SamplingProfile:
    temperature: float
    top_k: int
    min_p: float
    repetition_penalty: float
    presence_penalty: float | None = None
```

**CalibrationResult** (nuevo dataclass):
```python
@dataclass(slots=True, frozen=True)
class CalibrationResult:
    profile: SamplingProfile
    exam_id: str
    judge_scores: dict[str, float]
    composite_score: float
    adjusted_score: float
    response_length: int
    timestamp: str
```

**CalibrationReport** (nuevo dataclass):
```python
@dataclass(slots=True, frozen=True)
class CalibrationReport:
    timestamp: str
    total_iterations: int
    best_profile: SamplingProfile
    all_results: list[CalibrationResult]
    statistics: dict[str, Any]
```

### Algoritmo de Calibración

1. **Cargar prompts** de entrada (5-10 Investigation prompts)
2. **Inicializar estado** (verificar si existe checkpoint para resume)
3. **Para cada prompt**:
   - Para cada combinación de parámetros:
     - Generar respuesta con Student model
     - Enviar al Judge para evaluación
     - Calcular Composite Score
     - Aplicar penalización por longitud (<200 palabras)
     - Guardar resultado
4. **Seleccionar mejor perfil** por puntuación agregada
5. **Generar outputs**: calibration_report.json + vllm_config.yaml

### CLI Integration

Extender `src/audit/cli.py` con nuevo subcomando:
```bash
aegf calibrate --prompts prompts.json --output-dir ./calibration_results
```

### Integración con Componentes Existentes

- **InferenceRouter**: Reuse para llamadas al Student model
- **Judge**: Reuse llm_judge_score() para evaluación
- **Config**: Extender con nuevos parámetros de calibración
- **Schema**: Agregar nuevos dataclasses a schema.py

### Manejo de Errores y Resume

- Checkpoint en JSON después de cada iteración
- Formato: `{prompt_idx}_{profile_hash}_checkpoint.json`
- Al iniciar, verificar existencia de checkpoints y continuar desde el último
