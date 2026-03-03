# REFACTOR_TODO.md — Roadmap de Excelencia Arquitectónica
> Generado: 2026-03-03 | Basado en auditoría contra `AEGF.agent.md` v2.0
>
> Cada ítem lista: archivo, gravedad, violación, y path a la excelencia.

---

## Clasificación de Gravedad

| Nivel | Significado |
|-------|-------------|
| 🔴 **ALTA** | Viola leyes fundamentales (DRY, SRP, seguridad). Bloquea refactors seguros. |
| 🟠 **MEDIA** | Viola estándares de calidad (tipado, inmutabilidad, OCP). Degrada mantenibilidad. |
| 🟡 **BAJA** | Viola convenciones (logging format, dead code). Ruido técnico. |

---

## 🔴 GRAVEDAD ALTA

### 1. ~500 LOC duplicadas entre `production_v11.py` y `agentic_gen.py`
- **Archivos:** `src/factory/production_v11.py`, `src/factory/agentic_gen.py`
- **Violación:** DRY — 12+ funciones copiadas íntegramente entre ambos módulos.
- **Funciones duplicadas:**
  - `LEGACY_CODE_DETECTORS` (lista de regex)
  - `detect_legacy_patterns()`
  - `load_master_docs()`
  - `get_file_chunks()`
  - `get_fragments()`
  - `validate_ldi()`
  - `assign_example_type()`
  - `make_checkpoint_key()`
  - `load_checkpoint()`
  - `AsyncFileWriter`
  - `ProgressTracker`
  - `_prompt()`, `_render()`
- **Path a la excelencia:** Extraer a `src/factory/shared.py` (o sub-módulos: `src/factory/legacy_detection.py`, `src/factory/checkpoint.py`, `src/factory/fragmentation.py`). Ambos módulos importan del shared.

### 2. ✅ Zero test coverage — RESUELTO
- **Archivos:** `tests/` — creado con cobertura completa de los módulos `src/audit/` y `src/utils/`
- **129 tests passing, 1 skip contextual** (google-genai ImportError path, salta cuando el SDK está instalado)
- **Bug descubierto y corregido:** `ZeroDivisionError` en `stratified_sample([])` — `model_evaluator.py:215`
- **Módulos cubiertos:**
  - `tests/conftest.py` — factories y fixtures compartidas
  - `tests/test_schema.py` — SampleRecord, ExamRecord.from_sample(), ScoreCard, AuditReport, constantes
  - `tests/test_prompt_manager.py` — carga YAML, format, KeyError, missing keys
  - `tests/test_inference.py` — VLLMClient (mocked), retry + backoff, InferenceRouter caching
  - `tests/test_doc_loader.py` — happy path, FileNotFoundError por cada doc, edge cases
  - `tests/test_think_filter.py` — Sacred Constraint, no-op conditions, dedup mechanics, apply_to_record
  - `tests/test_sampling.py` — balance, determinism, edge cases, field population

### 3. `__init__.py` faltantes en paquetes
- **Archivos:** `src/factory/`, `src/discovery/`, `src/curation/`
- **Violación:** §5.5 — Paquetes Python Válidos.
- **Detalle:** Sin `__init__.py`, los imports relativos fallan y `python -m` no los reconoce como paquetes.
- **Path a la excelencia:** Crear `__init__.py` con `__all__` listando las APIs públicas de cada paquete.

### 4. API keys hardcodeadas en código fuente
- **Archivos:** `src/factory/production_v11.py` (L65), `src/factory/agentic_gen.py` (L43), `src/research/generate_batch_distilabel.py` (L160), `blackwell-trainer/scripts/synthesize.py`, `blackwell-trainer/src/data/debug_synth.py`
- **Violación:** §5.1 — Secretos y Configuración.
- **Detalle:** `"sk-master-bunker-2026"` hardcoded en 19 ubicaciones del workspace.
- **Path a la excelencia:** Reemplazar con `os.getenv("AEGF_API_KEY", "")`. Crear `.env.example` con las keys necesarias. Adicionar chequeo al arranque si la key está vacía.

### 5. `production_v11.py` es un monolito de 2237 LOC con 8+ responsabilidades
- **Archivo:** `src/factory/production_v11.py`
- **Violación:** §1.2 SRP — "Ningún módulo debe superar ~400 LOC sin justificación".
- **Responsabilidades mezcladas:** taxonomy loading, legacy detection, prompt building (Python + Jinja), AST fragmentation, LDI validation, sample generation, progress tracking, CLI orchestration.
- **Path a la excelencia:** Descomponer en:
  - `src/factory/taxonomy.py` — carga de taxonomía YAML
  - `src/factory/legacy_detection.py` — `LEGACY_CODE_DETECTORS`, `detect_legacy_patterns()`
  - `src/factory/fragmentation.py` — `get_fragments()`, `get_file_chunks()`, AST parsing
  - `src/factory/prompt_builder.py` — `build_system_*()`, `build_user_*()`, `_prompt()`, `_render()`
  - `src/factory/checkpoint.py` — `make_checkpoint_key()`, `load_checkpoint()`, `AsyncFileWriter`
  - `src/factory/production.py` — orquestador delgado que compone los bloques

### 6. `agentic_gen.py` es ~70% copia de `production_v11.py`
- **Archivo:** `src/factory/agentic_gen.py` (1040 LOC)
- **Violación:** DRY + SRP.
- **Path a la excelencia:** Tras extraer shared modules (ítem #1), reescribir como orquestador delgado que solo añade lógica de multi-turn + tool_calls. Target: <300 LOC.

---

## 🟠 GRAVEDAD MEDIA

### 7. `Dict[str, Any]` como tipo de fragmento — sin TypedDict
- **Archivos:** `src/factory/production_v11.py` (~30 ocurrencias), `src/factory/agentic_gen.py`, `src/curation/nemo_curator_suite.py`
- **Violación:** §2.1 — Prohibido `Dict[str, Any]` como sustituto de estructura conocida.
- **Path a la excelencia:** Definir `FragmentRecord(TypedDict)` con los campos conocidos: `name`, `source_file`, `code`, `example_type`, `ldi`, `metadata`, etc.

### 8. Dataclasses sin `slots=True` / `frozen=True`
- **Archivos:** `src/audit/schema.py` (`SampleRecord`, `ExamRecord`, `ScoreCard`, `AuditReport`), `src/discovery/processor.py` (`ModuleFile`, `Module`)
- **Violación:** §2.2 — Inmutabilidad por Defecto.
- **Detalle:** Los records de evaluación se mutan in-place (`s.ha_standards = ...`). Debería usarse un patrón builder o `dataclasses.replace()`.
- **Path a la excelencia:** Marcar como `@dataclass(slots=True, frozen=True)`. Donde se necesite mutar, usar `dataclasses.replace(s, ha_standards=new_value)`.

### 9. `ExamRecord` duplica todos los campos de `SampleRecord`
- **Archivo:** `src/audit/schema.py` (L128-152)
- **Violación:** DRY — 11 campos repetidos manualmente.
- **Path a la excelencia:** Usar herencia (`ExamRecord(SampleRecord)`) o composición (`sample: SampleRecord` como campo).

### 10. `generate_with_retry()` duplicada entre `GeminiClient` y `VLLMClient`
- **Archivo:** `src/audit/inference.py`
- **Violación:** DRY — la lógica de retry difiere solo en tipo de backoff (lineal vs exponencial).
- **Path a la excelencia:** Implementar retry como método template en `BaseInferenceClient` con `_backoff_delay(attempt)` como hook.

### 11. Dos implementaciones incompatibles de LDI
- **Archivos:** `src/factory/production_v11.py` → `validate_ldi()`, `src/curation/nemo_curator_suite.py` → `_ldi()`
- **Violación:** DRY + Corrección — misma métrica, fórmulas diferentes.
- **Path a la excelencia:** Extraer a `src/utils/ldi.py` con una sola implementación canónica, documentada con la fórmula y sus parámetros.

### 12. `SystemExit` usado como control de flujo
- **Archivo:** `src/audit/model_evaluator.py` (en `cmd_sample`, `cmd_generate_exam`)
- **Violación:** §5.4 — SystemExit no se usa como control de flujo.
- **Path a la excelencia:** Lanzar excepciones custom (`PipelineError`, `ValidationError`). Capturar en `main()` y traducir a exit code.

### 13. Side effects a nivel de módulo
- **Archivos:** `src/audit/model_evaluator.py` (`CFG = _load_config()` at module level), `src/research/generate_batch_distilabel.py` (lee archivos al importar), `src/factory/production_v11.py` (logger handler stacking)
- **Violación:** §5.3 — Import-Time Side Effects.
- **Path a la excelencia:** Mover inicialización a funciones `init()` o constructores explícitos. Lazy-load config solo cuando se necesite.

### 14. `load_master_docs()` nunca importada desde `doc_loader.py`
- **Archivos:** `src/factory/production_v11.py`, `src/factory/agentic_gen.py`
- **Violación:** DRY — `src/utils/doc_loader.py` fue creado para centralizar pero los consumidores principales siguen usando su propia copia.
- **Path a la excelencia:** Reemplazar las 2 implementaciones locales con `from src.utils.doc_loader import load_master_docs`.

### 15. `processor.py` — `_write_typed_bundle` y `_write_standalone_bundle` comparten 80% de lógica
- **Archivo:** `src/discovery/processor.py`
- **Violación:** DRY.
- **Path a la excelencia:** Extraer a `_write_bundle(files, template, ...)` parametrizado.

### 16. Dependencia directa de `AsyncOpenAI` en factory
- **Archivos:** `src/factory/production_v11.py`, `src/factory/agentic_gen.py`
- **Violación:** §1.2 DIP — Infraestructura instanciada en dominio.
- **Path a la excelencia:** Abstraer tras `BaseInferenceClient` (ya existe en `src/audit/inference.py`). Generalizar para que el factory también lo use, o crear `src/factory/inference.py` con la misma interfaz.

---

## 🟡 GRAVEDAD BAJA

### 17. f-strings en llamadas a logger
- **Archivos:** `src/discovery/ingestor.py`, `src/discovery/processor.py`, `src/curation/nemo_curator_suite.py`
- **Violación:** §2.4 — Usar lazy formatting.
- **Path a la excelencia:** Reemplazar `logger.info(f"Found {n}")` con `logger.info("Found %d", n)`.

### 18. Dead imports y código muerto
- **Archivos:**
  - `src/audit/model_evaluator.py`: `import hashlib` sin uso real, `import random` desplazado con noqa
  - `src/discovery/ingestor.py`: bloque `if __name__` nunca invoca `engine.run()`
  - `src/curation/nemo_curator_suite.py`: `import shutil` duplicado en dos sitios
- **Violación:** Code noise.
- **Path a la excelencia:** Ejecutar `ruff check --select F401,F811` y limpiar.

### 19. `generate_batch_distilabel.py` — script experimental acoplado
- **Archivo:** `src/research/generate_batch_distilabel.py`
- **Violación:** SRP, DIP, Import-Time Side Effects — peor módulo del codebase.
- **Path a la excelencia:** Mantener en `src/research/` con documentación clara de que es experimental. NO importar desde otros módulos. Considerar mover a `scripts/` o `notebooks/`.

### 20. `blackwell-trainer/src/` — tipado casi inexistente
- **Archivos:** `src/core/trainer.py`, `src/data/audit.py`, `src/data/collect.py`, `src/data/analisis_dataset.py`, `src/utils/observability.py`, `src/utils/thermal.py`
- **Violación:** §2.1 — Tipado Estricto.
- **Detalle:** Promedio 1.2/5 en typing. Solo `divide_dataset.py` tiene anotaciones.
- **Path a la excelencia:** Añadir type hints a todas las firmas. Priorizar `trainer.py` (módulo core).

### 21. `blackwell-trainer/` — paths absolutos y scripts top-level
- **Archivos:** `src/data/audit.py` (path absoluto a `/mnt/bunker_data/...`), `src/data/analisis_dataset.py` (path a modelo con typo), `src/core/trainer.py` (ejecuta al importar)
- **Violación:** §5.1 + §5.3.
- **Path a la excelencia:** Convertir en funciones con `argparse` o recibir paths como parámetro. Encapsular lógica de `trainer.py` en `def train(config_path: Path)`.

### 22. Estado global mutable en factory
- **Archivos:** `src/factory/production_v11.py` (`_TAX`, `HA_ERROR_TEMPLATES`, `LEGACY_2023_PATTERNS`)
- **Violación:** §3.3 — Desacoplamiento de Estado.
- **Path a la excelencia:** Encapsular en instancia de `TaxonomyConfig(frozen=True)` cargada una vez y pasada como parámetro.

### 23. `Pydantic config` en `ingestor.py` — mutable con mutación post-construcción
- **Archivo:** `src/discovery/ingestor.py` (L209: `config.github_token = token`)
- **Violación:** §2.2 — Inmutabilidad por Defecto.
- **Path a la excelencia:** Usar `model_copy(update={...})` de Pydantic v2 o constructor con override.

### 24. Error handling — bare `except` y errores silenciados
- **Archivos:**
  - `src/factory/production_v11.py`: bare `except Exception` + `pass` en parseo AST (L904, L1037)
  - `blackwell-trainer/src/utils/observability.py`: `except: pass` múltiple
  - `src/discovery/ingestor.py`: git clone con `check=False` sin logging de stderr
- **Violación:** §5.4.
- **Path a la excelencia:** Capturar excepciones específicas. Loggear siempre. Nunca `pass` sin comentario.

---

## Resumen ejecutivo

| Gravedad | Ítems | Esfuerzo estimado |
|----------|-------|-------------------|
| 🔴 Alta | 6 | ~3-5 días de refactoring concentrado |
| 🟠 Media | 10 | ~3-4 días adicionales |
| 🟡 Baja | 8 | ~1-2 días (pueden hacerse incrementalmente) |

### Orden de ejecución recomendado

1. **#2 Tests** — Sin tests, cualquier refactor es un acto de fe. Crear tests primero.
2. **#3 `__init__.py`** — Prerequisito para imports limpios.
3. **#1 + #6 Extracción de shared modules** — Elimina el 70% de la duplicación.
4. **#4 API keys** — Fix de seguridad, 30 minutos.
5. **#5 Descomposición de `production_v11.py`** — El Big Refactor.
6. **#7-#16 Tipado, inmutabilidad, Strategy** — Mejoras incrementales.
7. **#17-#24 Limpieza** — Polish final.

---

*Este documento es efímero. A medida que se resuelvan ítems, deben marcarse como ✅ completados o eliminarse.*
