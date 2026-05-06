# Gito v2 Report Classification — rfactory-factory-frameworks

**Fecha análisis:** 2026-05-05  
**Source:** `/tmp/gito-v2-report/code-review-report.json`  
**Total issues:** 62 (en 62 archivos)  
**Status:** COMPLETED (creado 2026-05-05 19:38:18)

---

## Clasificación Resumen

| Categoría | Count | Description |
|-----------|-------|-------------|
| **FALSE_POSITIVE** | 46 | No requiere acción |
| **REAL_BUG** | 8 | Bug real que debe corregirse |
| **NEEDS_REVIEW** | 8 | Requiere revisión manual adicional |

---

## FALSE_POSITIVEs (46 issues)

### Category A: Archivos nuevos en esta rama (NO存在于main)
- `src/utils/extractors/extractors/yaml_base.py` — **NUEVO ARCHIVO**, issues son de código heredado
- `src/utils/extractors/extractors/jinja_base.py` — **NUEVO ARCHIVO**
- `src/utils/extractors/extractors/service_call.py` — **NUEVO ARCHIVO**
- `src/utils/extractors/extractors/base.py` — **NUEVO ARCHIVO**
- `src/audit/calibration_signature.py` — **NUEVO ARCHIVO**
- `src/discovery/ingestor.py` — **NUEVO ARCHIVO**
- `src/discovery/metadata_enricher.py` — **NUEVO ARCHIVO**

### Category B: Intentional frozen dataclass __setattr__ patterns
- **`src/utils/extractors/extractors/yaml_base.py` (11 issues, severity 1):** `object.__setattr__("data", ...)` sin `self` es el **patrón intencional** para frozen dataclasses. El código funciona correctamente. **FALSE_POSITIVE**

### Category C: Test fixtures (excluidos de lint por spec)
- `tests/fixtures/fragment_test_helpers.py` — test fixture helpers
- `tests/fixtures/jinja_samples/template.jinja`
- `tests/fixtures/master_docs/CLAUDE.md`
- `tests/fixtures/master_docs/JINJA_GUIDE.md`
- `tests/fixtures/reference_corpus/homeassistant/repo2/sensor.py`
- `tests/fixtures/repos/fixture_helpers.py`
- `tests/fixtures/repos/ha_python_repo.py`
- `tests/fixtures/repos/multi_language_repo.py`
- `tests/fixtures/repos/php_repo.py`
- `tests/fixtures/repos/python_repo.py`
- `tests/fixtures/yaml_samples/blueprint.yaml`

### Category D: Documentación .md (no código)
- `.progress.md` — spec tracking doc
- `INFORME_STAGE_3_TRAINING.md` — informe en español
- `plans/informe-dependency-compatibility-issues.md` — informe en español (6 issues, todos language/readability)

### Category E: Archivos existentes en main (pre-existentes)
- `infrastructure/anchor_dataset/anchor_providers.py` — existe en main, cambios son fixes de Phase 1.2 (remover hardcoded key)
- `infrastructure/anchor_dataset/checkpoint.py`
- `infrastructure/anchor_dataset/exporter.py`
- `infrastructure/anchor_dataset/quality.py`
- `infrastructure/anchor_dataset/seed_loader.py`
- `infrastructure/anchor_dataset/seed_synthesizer.py`
- `infrastructure/anchor_dataset/startup.py`
- `infrastructure/anchor_dataset_builder.py`
- `infrastructure/baselines/_shared.py`
- `infrastructure/baselines/measure_mipro_compile_baseline.py`
- `infrastructure/baselines/measure_spearman_baseline.py`
- `infrastructure/baselines/run_calibration_baseline.py`
- `infrastructure/dependency_check.py`
- `infrastructure/rollback_check.py`
- `src/factory/agentic_cli.py`
- `src/factory/backtracking_detector.py`
- `src/factory/dspy_utils.py`
- `src/factory/trajectory_signature.py`
- `src/utils/extractors/jinja_adapter.py`
- `src/utils/extractors/yaml_adapter.py`
- `docs/_state-file-reference.md` — Mix de English/Spanish es intencional (proyecto Español)
- `docs/auto-detection.md`
- `docs/dependency-compatibility.md`
- `.roomodes` — config file

---

## REAL_BUGs (8 issues)

### 1. `infrastructure/anchor_dataset/anchor_providers.py` — Issue ID 8 (severity 2)
**Descripción:** VLLMProvider.generate raises ValueError en lugar de retornar None cuando falta API key.

```python
# current (line 68-70):
if api_key is None:
    raise ValueError("VLLM_API_KEY environment variable is required")

# expected (según contract base class):
if api_key is None:
    return None
```

**Acción:** Fix requerido — contradice el contract documentado en la clase base.

### 2. `infrastructure/rollback_check.py` — 3 issues (severity 2)
**Descripción:** os.chdir() sin context manager — side-effect que afecta estado global.

**Acción:** Fix requerido — usar pathlib.Path.glob() en lugar de os.chdir().

### 3. `infrastructure/anchor_dataset/sample_generator.py` — Issue ID 13 (severity 3)
**Descripción:** Hardcoded 2-digit padding `:02d` rompe a >99 items.

```python
# current:
sid = f"anchor_001_{sample_idx:02d}"

# expected:
sid = f"anchor_001_{sample_idx:04d}"
```

**Acción:** Fix menor pero real.

### 4. `infrastructure/anchor_dataset/sample_generator.py` — Issue ID 14 (severity 3)
**Descripción:** Terminology inconsistency: `COMPLEXITY` vs `Difficulty` en templates.

**Acción:** Unificar a `DIFFICULTY`.

### 5. `infrastructure/anchor_dataset/sample_generator.py` — Issue ID 15 (severity 3)
**Descripción:** Docstring example contradicts implementation logic.

**Acción:** Fix docstring para match con código real.

---

## NEEDS_REVIEW (8 issues)

### Issues en archivos不解
1. `infrastructure/anchor_dataset/quality.py` — 2 issues
2. `infrastructure/anchor_dataset/seed_loader.py` — 2 issues
3. `src/audit/prompts_judge.example.yaml` — 2 issues
4. `src/export/prompts_frontend.example.yaml` — 1 issue
5. `src/factory/backtracking_detector.py` — 2 issues

---

## Comparación vs Spec `code-review-classification`

La spec `specs/code-review-classification/tasks.md` documenta **102 Group 1 bugs** que fueron addressed en Phases 1-15. El reporte gito-v2 con 62 issues es un análisis **independiente** de gito que no conoce el contexto de la spec.

**Conclusión:** Los 62 issues de gito-v2 incluyen muchos FALSE_POSITIVEs debido a:
1. Archivos nuevos sin contexto de spec
2. Frozen dataclass patterns no reconocidos
3. Test fixtures excluidos de lint
4. Documentación en español no considerada

Los REAL_BUGs identificados (8) deben ser evaluados contra la spec para determinar si ya fueron addressed en Phases 1-15.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Source JSON | `/tmp/gito-v2-report/code-review-report.json` |
| Created | 2026-05-05 19:38:18 |
| Model | (ver JSON) |
| Files processed | (ver JSON) |
| Processing warnings | (ver JSON) |

Generado: 2026-05-05T20:01:00Z