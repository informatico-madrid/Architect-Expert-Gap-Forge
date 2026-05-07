# INFORME DETALLADO: STAGE 2 FACTORY - GENERACIÓN DE DATOS DE ENTRENAMIENTO

## 1. VISIÓN GENERAL DEL STAGE 2

El **Stage 2** (llamado **Factory**) es un sistema de generación de datos de entrenamiento sintéticos para modelos LLM. Su propósito es generar muestras de entrenamiento diversificadas a partir de fragmentos de código extraídos de repositorios reales.

**Ubicación del código:** `src/factory/`
**Documentación:** `docs/METHODOLOGY.md`

---

## 2. ARQUITECTURA DEL PIPELINE

El Stage 2 implementa un pipeline de **generación asíncrona** con varios modos de operación:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     STAGE 2 FACTORY PIPELINE                        │
└─────────────────────────────────────────────────────────────────────┘

INPUT: data/raw/*.txt (fragmentos extraídos de repositorios)
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PASS 1: Scan & Parse                                                │
│  - Detectar MODULE_BLUEPRINT, GOVERNANCE_RULES                      │
│  - Extraer FUNCTIONAL_UNIT, LOGIC_ONLY bundles                      │
│  - Build blueprint/governance cache in RAM                          │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PASS 2: Fragment Generation                                         │
│  - Extraer fragments de FUNCTIONAL_UNIT/LOGIC_ONLY                  │
│  - Inyectar blueprint context                                      │
│  - Detectar legacy patterns                                         │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  EXAMPLE TYPE ASSIGNMENT                                             │
│  - legacy_detected=True  → contrast/error_recovery                  │
│  - clean code            → nominal                                  │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ASYNC SAMPLE GENERATION (vLLM API)                                │
│  - Concurrency control via semaphore                               │
│  - Gold Injection (anti-schizophrenia filter)                      │
│  - LDI Validation (reasoning depth)                                │
│  - Post-validation (poison patterns)                               │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
OUTPUT: data/synthetic/v11_diversified_YYYYMMDD_HHMMSS.jsonl
```

---

## 3. COMANDOS PARA EJECUTAR STAGE 2

### 3.1 Comando Principal: Factory CLI

El script principal está ubicado en: `src/factory/cli.py`

#### 3.1.1 Ejecución Completa (Diversified Mode)

```bash
cd /mnt/bunker_data/ai/data_factory

# Ejecución básica
python -m src.factory.cli \
    --raw-dir data/raw \
    --output data/synthetic/v11_diversified_20260301_120000.jsonl \
    --gap-dir data/Gap \
    --base-url http://localhost:8000/v1 \
    --api-key tu-api-key-aqui \
    --model qwen3-30b-a3b-thinking-fp8 \
    --workers 16 \
    --resume checkpoints/checkpoint.jsonl \
    --apply

# Ejecución en modo teoría (solo doctrina HA 2026)
python -m src.factory.cli \
    --theory \
    --theory-reps 3 \
    --raw-dir data/raw \
    --output data/synthetic/v11_theory_20260301_120000.jsonl \
    --gap-dir data/Gap \
    --base-url http://localhost:8000/v1 \
    --api-key tu-api-key-aqui \
    --model qwen3-30b-a3b-thinking-fp8 \
    --workers 16
```

#### 3.1.2 Parámetros Principales

| Parámetro | Descripción | Requerido |
|-----------|-------------|-----------|
| `--raw-dir` | Directorio con fragmentos .txt de Stage 1 | Sí |
| `--output` | Archivo JSONL de salida | Sí |
| `--gap-dir` | Directorio con master docs (HA_MASTER_GUIDE_2026.md) | Sí |
| `--base-url` | URL del endpoint vLLM API | Sí |
| `--api-key` | API key para autenticación | Sí |
| `--model` | Modelo LLM a usar | Sí |
| `--workers` | Workers asíncronos concurrentes | No (default: 8) |
| `--resume` | Archivo checkpoint para reanudar | No |
| `--apply` | Escribir salida (si no, dry-run) | No |

#### 3.1.3 Parámetros de Configuración

| Parámetro | Descripción |
|-----------|-------------|
| `--taxonomy` | Ruta al archivo YAML de taxonomía |
| `--theory` | Modo teoría (doctrina HA 2026) |
| `--theory-reps` | Repeticiones para modo teoría |
| `--test` | Limitar a N fragmentos para testing |
| `--limit` | Limitar a N archivos |
| `--extensions` | Filtrar por extensiones (.py, .yaml, etc.) |
| `--think-filter` | Aplicar think filter (distillation) |
| `--think-filter-min-chars` | Mínimo chars para think filter |

---

## 4. CONFIGURACIÓN DETALLADA

### 4.1 Configuración de Taxonomía (`configs/stage_2_factory/taxonomy/`)

La taxonomía define prompts, error templates y patrones legacy:

```yaml
# configs/stage_2_factory/taxonomy/home_assistant/prompts_taxonomy.yaml
prompts:
  user:
    python:
      nominal_easy: |
        Contexto: $context
        Archivo: $virtual_filename
        Tarea: Implementa `$name` siguiendo el estándar Home Assistant 2026.
        Esqueleto: $skeleton
        Genera la implementación usando el bloque <write_action>.

      contrast: |
        Contexto: $context
        Estoy implementando `$name` y tengo este código funcionando:
        ```python
        $legacy_code
        ```
        ¿Puedes completar la implementación usando este mismo estilo?
        Esqueleto actual: $skeleton
        Genera el archivo completo usando <write_action>.

  system:
    python: |
      Eres un Agente Experto y Arquitecto de Software en Home Assistant (2026).
      Tu objetivo es implementar soluciones técnicas robustas.

      HERRAMIENTAS DISPONIBLES:
      $tools_json

      ANCLAS DE VERDAD:
      - DEBES usar las LEYES y reglas del MANUAL ADJUNTO como "Anclas de Verdad"
      - Si tu razonamiento contradice las Leyes del MANUAL, considera el output inválido

      ==== BEGIN MASTER GUIDE ====
      $master
      ==== END MASTER GUIDE ====

      ==== BEGIN TECHNICAL CHANGELOG ====
      $changelog
      ==== END TECHNICAL CHANGELOG ====
```

### 4.2 Error Templates

```yaml
# configs/stage_2_factory/taxonomy/home_assistant/prompts_taxonomy.yaml
ha_error_templates:
  - error: >-
      InvalidStateError: Entity {entity} uses deprecated TEMP_CELSIUS.
      UnitOfTemperature.CELSIUS must be used instead.
    category: enum_migration
    legacy_pattern: "TEMP_CELSIUS"
    modern_fix: "UnitOfTemperature.CELSIUS"

  - error: >-
      DeprecationWarning: async_forward_entry_setup is deprecated.
      Use async_forward_entry_setups (plural) instead.
    category: setup_migration
    legacy_pattern: "async_forward_entry_setup"
    modern_fix: "async_forward_entry_setups"
```

### 4.3 Legacy Patterns (Contrast)

```yaml
legacy_2023_patterns:
  - title: "hass.data vs entry.runtime_data"
    legacy_code: |
      hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    modern_code: |
      entry.runtime_data = MyRuntimeData(coordinator=coordinator)
    explanation: >-
      En 2023 se usaba el diccionario global hass.data.
      En 2026, entry.runtime_data con dataclass tipada es obligatorio.
```

---

## 5. FLUJO DE EJECUCIÓN

### 5.1 Paso 1: Extraer Fragmentos de Stage 1

Primero necesitas ejecutar Stage 1 Discovery para extraer fragmentos:

```bash
# Stage 1: Discovery (ya ejecutado)
# Output: data/raw/*.txt

# Verificar fragmentos generados
ls -la data/raw/
```

### 5.2 Paso 2: Preparar Master Docs

```bash
# Master docs deben estar en data/Gap
ls -la data/Gap/

# Debe contener:
# - HA_MASTER_GUIDE_2026.md
# - CHANGELOG.md
```

### 5.3 Paso 3: Ejecutar Factory

```bash
# Ejecución completa
cd /mnt/bunker_data/ai/data_factory

python -m src.factory.cli \
    --raw-dir data/raw \
    --output data/synthetic/v11_diversified_20260301_120000.jsonl \
    --gap-dir data/Gap \
    --base-url http://localhost:8000/v1 \
    --api-key tu-api-key-aqui \
    --model qwen3-30b-a3b-thinking-fp8 \
    --workers 16 \
    --apply
```

### 5.4 Paso 4: Verificar Output

```bash
# Verificar output generado
wc -l data/synthetic/v11_diversified_20260301_120000.jsonl

# Ver distribución de example types
python -c "
import json
from collections import Counter

counts = Counter()
with open('data/synthetic/v11_diversified_20260301_120000.jsonl') as f:
    for line in f:
        rec = json.loads(line)
        etype = rec['metadata']['example_type']
        counts[etype] += 1

print('Distribution:')
for etype, count in counts.items():
    print(f'  {etype}: {count}')
"
```

---

## 6. TIPOS DE EJEMPLOS GENERADOS

### 6.1 Distribution Target

El Stage 2 genera una distribución balanceada:

| Example Type | Percentage | Description |
|--------------|------------|-------------|
| `nominal` | 50% | Implementación estándar 2026 |
| `contrast` | 30% | Modernización de código legacy |
| `error_recovery` | 20% | Diagnóstico y corrección de errores |

### 6.2 Ejemplo de Output JSONL

```json
{
  "id": "v11_nominal_abc123def456",
  "conversation": [
    {
      "role": "user",
      "content": "Contexto: ... Archivo: ... Tarea: Implementa ..."
    },
    {
      "role": "assistant",
      "content": "<think>\nRazonamiento técnico...\n</think>\n<write_action>\n<path>custom_components/my_integration/__init__.py</path>\n<content>...código...</content>\n</write_action>"
    }
  ],
  "metadata": {
    "curation": {
      "kept": true,
      "quality_score": 0.0
    },
    "factory_version": "v11.0",
    "example_type": "nominal",
    "evol_difficulty": "hard",
    "ldi": 1.25,
    "fragment_name": "Module: config_flow",
    "source_file": "custom_components/my_integration/__init__.py",
    "gold_injected": true,
    "legacy_detected": false,
    "legacy_patterns": [],
    "checkpoint_key": "abc123def456"
  },
  "filter_text": "Razonamiento completo para deduplicación"
}
```

---

## 7. ALGORITMOS Y VALIDACIONES

### 7.1 LDI (Logic Density Index) Validation

El LDI valida que el reasoning tenga suficiente densidad lógica:

```python
# src/factory/ldi_validator.py

def validate_ldi(code_len: int, reasoning_len: int, subtype: str) -> LDIResult:
    """Validate reasoning depth relative to code length."""
    ratio = reasoning_len / max(code_len, 1)

    if subtype == "functional_unit":
        threshold = 0.5
    elif subtype == "code":
        threshold = 0.3
    else:
        threshold = 0.2

    is_valid = ratio >= threshold
    score = min(1.0, ratio / threshold)

    return LDIResult(is_valid=is_valid, score=score, reason=...)
```

### 7.2 Gold Injection (Anti-Schizophrenia Filter)

```python
# src/factory/pipeline_runner.py

# Detect legacy patterns
legacy_patterns = detect_legacy_patterns(frag.get("original", ""))
has_legacy = len(legacy_patterns) > 0

# If legacy detected, SKIP gold injection
# This prevents CoT schizophrenia: think=2026, code=legacy
if not has_legacy:
    # Clean output -> safe gold injection
    gold_injected = True
else:
    # Keep model code (2026)
    gold_injected = False
```

### 7.3 Post-Validation

```python
# Detect poison patterns (toxic outputs)
poison_patterns = post_validate_output(
    generated_code,
    example_type,
    frag.get("subtype", "code")
)

# Auto-reject if poison patterns found
if poison_patterns:
    is_kept = False
    logger.warning(f"POISON: {frag['name']} - {poison_patterns}")
```

---

## 8. RESUME CAPABILITY

El pipeline soporta reanudar desde checkpoint:

```bash
# Checkpoint file format
cat checkpoints/checkpoint.jsonl
# {"fragment_name": "...", "checkpoint_key": "..."}

# Reanudar desde checkpoint
python -m src.factory.cli \
    --raw-dir data/raw \
    --output data/synthetic/v11_diversified.jsonl \
    --resume checkpoints/checkpoint.jsonl \
    --apply
```

---

## 9. OUTPUT ARTIFACTS

### 9.1 Main Output

```
data/synthetic/v11_diversified_YYYYMMDD_HHMMSS.jsonl
```

### 9.2 Rejected Samples

```
data/synthetic/v11_rejected_YYYYMMDD_HHMMSS.jsonl
```

### 9.3 Theory Output (si --theory)

```
data/synthetic/v11_theory_YYYYMMDD_HHMMSS.jsonl
data/synthetic/v11_theory_rejected_YYYYMMDD_HHMMSS.jsonl
```

---

## 10. PIPELINE COMPLETO DE EJECUCIÓN

### 10.1 Script Completo

```bash
#!/bin/bash
# Stage 2 Factory Pipeline - Ejecución completa

set -e

cd /mnt/bunker_data/ai/data_factory

# ── STEP 1: Verify Stage 1 output ──────────────────────────────────
echo "=== Stage 1: Discovery Output Check ==="
ls -la data/raw/*.txt | head -10
fragment_count=$(ls data/raw/*.txt | wc -l)
echo "Found $fragment_count fragments from Stage 1"

# ── STEP 2: Verify Master Docs ─────────────────────────────────────
echo "=== Stage 2: Master Docs Check ==="
ls -la data/Gap/
echo "Master Guide: $(wc -c < data/Gap/HA_MASTER_GUIDE_2026.md) chars"
echo "Changelog: $(wc -c < data/Gap/CHANGELOG.md) chars"

# ── STEP 3: Run Factory ────────────────────────────────────────────
echo "=== Stage 2: Factory Execution ==="
python -m src.factory.cli \
    --raw-dir data/raw \
    --output data/synthetic/v11_diversified_$(date +%Y%m%d_%H%M%S).jsonl \
    --gap-dir data/Gap \
    --base-url http://localhost:8000/v1 \
    --api-key tu-api-key-aqui \
    --model qwen3-30b-a3b-thinking-fp8 \
    --workers 16 \
    --apply

# ── STEP 4: Verify Output ──────────────────────────────────────────
echo "=== Stage 2: Output Verification ==="
output_file="data/synthetic/v11_diversified_$(date +%Y%m%d_%H%M%S).jsonl"
record_count=$(wc -l < "$output_file")
echo "Generated $record_count training samples"

# Distribution analysis
python -c "
import json
from collections import Counter

counts = Counter()
with open('$output_file') as f:
    for line in f:
        rec = json.loads(line)
        etype = rec['metadata']['example_type']
        counts[etype] += 1

print('Distribution:')
total = sum(counts.values())
for etype in ['nominal', 'contrast', 'error_recovery', 'theory']:
    pct = counts[etype] / total * 100 if total > 0 else 0
    print(f'  {etype}: {counts[etype]} ({pct:.1f}%)')
"

echo "=== Stage 2 Complete ==="
```

---

## 11. ARCHIVOS Y ESTRUCTURA DEL PROYECTO

```
/mnt/bunker_data/ai/data_factory/
├── src/
│   └── factory/
│       ├── cli.py                    ← CLI principal
│       ├── pipeline_runner.py        ← Pipeline core (async)
│       ├── prompt_builder.py         ← System/user prompt builders
│       ├── fragment_extractor.py     ← Fragment extraction (Pass 1/2)
│       ├── hard_query_builder.py     ← Hard query generation
│       ├── ldi_validator.py          ← LDI validation
│       ├── think_filter.py           ← Reasoning distillation
│       ├── checkpoint.py             ← Checkpoint/resume logic
│       ├── agentic_runner.py         ← Agentic execution
│       ├── agentic_teacher_client.py ← Teacher model client
│       └── config.py                 ← Configuration
│
├── configs/
│   └── stage_2_factory/
│       └── taxonomy/
│           ├── home_assistant/
│           │   ├── prompts_taxonomy.yaml
│           │   ├── agentic_taxonomy.yaml
│           │   └── plugin_architecture.yaml
│           └── generic_domain/
│               ├── *.yaml.example
│
├── data/
│   ├── raw/                          ← Stage 1 output
│   ├── synthetic/                    ← Stage 2 output
│   └── Gap/                          ← Master docs
│       ├── HA_MASTER_GUIDE_2026.md
│       └── CHANGELOG.md
```

---

## 12. RESUMEN DE ACCIONES

### 12.1 Comandos Principales

1. **Ejecución básica:**
   ```bash
   python -m src.factory.cli \
       --raw-dir data/raw \
       --output data/synthetic/output.jsonl \
       --gap-dir data/Gap \
       --base-url http://localhost:8000/v1 \
       --api-key KEY \
       --model qwen3-30b-a3b-thinking-fp8 \
       --workers 16 \
       --apply
   ```

2. **Modo teoría:**
   ```bash
   python -m src.factory.cli \
       --theory \
       --theory-reps 3 \
       --raw-dir data/raw \
       --output data/synthetic/theory.jsonl \
       --gap-dir data/Gap \
       --base-url http://localhost:8000/v1 \
       --api-key KEY \
       --apply
   ```

3. **Resume from checkpoint:**
   ```bash
   python -m src.factory.cli \
       --raw-dir data/raw \
       --output data/synthetic/output.jsonl \
       --resume checkpoints/checkpoint.jsonl \
       --apply
   ```

### 12.2 Verificación

```bash
# Check Stage 1 output
ls data/raw/*.txt | wc -l

# Check Master docs
ls data/Gap/

# Run factory
python -m src.factory.cli --raw-dir data/raw --output output.jsonl --gap-dir data/Gap --apply

# Verify output
wc -l output.jsonl
```

---

## 13. NOTAS IMPORTANTES

1. **Stage 1 prerequisite**: Stage 2 requiere output de Stage 1 (`data/raw/*.txt`)
2. **Master docs**: `HA_MASTER_GUIDE_2026.md` y `CHANGELOG.md` son obligatorios
3. **vLLM API**: Requiere endpoint vLLM ejecutándose (`http://localhost:8000/v1`)
4. **Gold Injection**: Solo se aplica si no hay legacy patterns detectados
5. **Think Filter**: Por defecto activo, puede desactivarse con `--no-think-filter`
6. **Checkpoint**: Los checkpoints permiten resumir ejecuciones interrumpidas

---

**Documento generado:** 2026-04-01
**Versión:** Stage 2 v11.0
**Estado:** Documentación completa
