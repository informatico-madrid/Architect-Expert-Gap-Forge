# INFORME DETALLADO: STAGE 3 TRAINING - CURACIÓN DE DATOS

## 1. VISION GENERAL DEL STAGE 3

El **Stage 3** (también llamado **Stage 3 Curation**) es un pipeline de curación de datos de alta calidad para datasets de entrenamiento de modelos de lenguaje. Su propósito es limpiar, deduplicar y filtrar muestras de entrenamiento para asegurar que solo las muestras de máxima calidad entren en el proceso de training.

**Ubicación del código:** `src/curation/`
**Documentación:** `docs/specs/stage_1_5_backtracking_alignment.md`

---

## 2. ARQUITECTURA DEL PIPELINE

El Stage 3 implementa un pipeline de **4 fases** que procesan los datos secuencialmente:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGE 3 CURATION PIPELINE                        │
└─────────────────────────────────────────────────────────────────────┘

INPUT: data/synthetic/v11_diversified_YYYYMMDD_HHMMSS.jsonl
        │
        ▼
┌───────────────────────┐
│  PHASE 0: Exact Dedup │  ← Deduplicación SHA-256 (in-memory)
│     (0.5%)            │     Elimina duplicados exactos
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ PHASE 1: NeMo Filter  │  ← Pipeline distribuido Ray (container)
│     (5-10%)           │     Filtrado por calidad de texto
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  PHASE 2: Structural  │  ← Filtros de calidad estructural
│     (10-15%)          │     - Syntax checking
│                       │     - Think-depth validation
│                       │     - LDI ratio
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│   PHASE 3: Semantic   │  ← Deduplicación semántica
│      Dedup            │     MinHash-LSH para similitud
│      (2-5%)           │
└──────────┬────────────┘
           │
           ▼
OUTPUT: data/curated/v11_curated_YYYYMMDD_HHMMSS.jsonl
```

---

## 3. COMANDOS PARA EJECUTAR STAGE 3

### 3.1 Comando Principal: Curator Suite

El script principal está ubicado en: `src/curation/curator_cli.py`

#### 3.1.1 Ejecución Completa (4 Fases)

```bash
cd /mnt/bunker_data/ai/data_factory

# Paso 1: Arrancar el container de curación
cd deploy/docker && docker compose up -d curator

# Paso 2: Acceder al container
docker exec -it aegf_curator bash

# Paso 3: Ejecutar el pipeline completo
python -m src.curation.curator_cli \
    --input data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl \
    --output data/curated/v11_curated_20260301_120000.jsonl \
    --exact-dedup \
    --filter \
    --structural \
    --dedup \
    --apply
```

#### 3.1.2 Ejecución de Fases Individuales

**Solo Phase 0 (Exact Dedup):**
```bash
python -m src.curation.curator_cli \
    --input data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl \
    --output data/curated/phase0_dedup.jsonl \
    --exact-dedup \
    --apply
```

**Solo Phase 1 (NeMo Filter):**
```bash
# Requiere estar dentro del container aegf_curator
python -m src.curation.curator_cli \
    --input data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl \
    --output data/curated/phase1_filter.jsonl \
    --filter \
    --apply
```

**Solo Phase 2 (Structural):**
```bash
python -m src.curation.curator_cli \
    --input data/curated/phase1_filter.jsonl \
    --output data/curated/phase2_structural.jsonl \
    --structural \
    --apply
```

**Solo Phase 3 (Semantic Dedup):**
```bash
python -m src.curation.curator_cli \
    --input data/curated/phase2_structural.jsonl \
    --output data/curated/phase3_semantic.jsonl \
    --dedup \
    --apply
```

---

## 4. PARAMETROS DETALLADOS

### 4.1 Parámetros de I/O

| Parámetro | Descripción | Requerido |
|-----------|-------------|-----------|
| `--input` | Archivo JSONL de entrada | Sí (para fases 0-3) |
| `--output` | Archivo JSONL de salida | Sí (para fases 0-3) |
| `--reports-dir` | Directorio para reports JSON | No (default: `data/reports`) |
| `--apply` | Escribir salida (si no, dry-run) | No (default: false) |
| `--sample` | Procesar solo N primeros registros | No (default: 0 = todos) |

### 4.2 Parámetros de Phase 1 - NeMo Filter

| Parámetro | Valor Por Defecto | Descripción |
|-----------|-------------------|-------------|
| `--min-words` | 20 | Palabras mínimas en el texto |
| `--max-symbol-ratio` | 0.50 | Máximo ratio de símbolos |
| `--max-non-alpha-ratio` | 0.65 | Máximo ratio de caracteres no alfanuméricos |
| `--max-url-ratio` | 0.30 | Máximo ratio de URLs |
| `--max-no-endmark-ratio` | 0.99 | Máximo ratio de oraciones sin punto final |
| `--max-boilerplate-ratio` | 0.85 | Máximo ratio de texto boilerplate |
| `--max-repeated-lines` | 0.90 | Máximo fraction de líneas repetidas |
| `--max-ngram-ratio` | 0.35 | Máximo ratio de n-grams repetidos |
| `--ngram-size` | 3 | Tamaño de n-gram para detección |

### 4.3 Parámetros de Phase 2 - Structural

| Parámetro | Valor Por Defecto | Descripción |
|-----------|-------------------|-------------|
| `--min-think-chars` | 100 | Mínimo caracteres en bloque `<think>` |
| `--ldi-min-ratio` | 0.02 | Mínimo ratio LDI (Logic Density Index) |
| `--no-attempt-check` | false | Desactivar check de `attempt_completion` |

### 4.4 Parámetros de Phase 3 - Semantic Dedup

| Parámetro | Valor Por Defecto | Descripción |
|-----------|-------------------|-------------|
| `--dedup-threshold` | 0.85 | Umbral de similitud MinHash |
| `--quality-cutoff` | 0.50 | Puntuación mínima de calidad heurística |
| `--minhash-perms` | 128 | Número de permutaciones MinHash |
| `--shingle-k` | 5 | Tamaño de shingle de caracteres |

---

## 5. COMANDO MIX-DATASETS (Stage 3 Enhancement)

El Stage 3 también incluye un comando especial para combinar datasets especializados con datasets de anclaje (anchor datasets).

### 5.1 Ejecución del Mix-Datasets

```bash
python -m src.curation.curator_cli \
    --mix-datasets \
    --specialized-jsonl data/curated/v11_curated_20260301_120000.jsonl \
    --anchor-configs configs/stage_3_curation/anchors.yaml \
    --output-jsonl data/mixed/v11_mixed_20260301_120000.jsonl \
    --seed 42 \
    --specialized-pct 30.0 \
    --anchor-pct 70.0 \
    --report data/reports/composition_report.json \
    --apply
```

### 5.2 Parámetros del Mix-Datasets

| Parámetro | Descripción | Valor Por Defecto |
|-----------|-------------|-------------------|
| `--mix-datasets` | Activar modo mix-datasets | Sí (si se usa) |
| `--specialized-jsonl` | Ruta al dataset especializado | Requerido |
| `--anchor-configs` | Ruta al config YAML de anchors | Requerido |
| `--output-jsonl` | Ruta de salida JSONL | Requerido |
| `--seed` | Seed para shuffle determinístico | 42 |
| `--specialized-pct` | % tokens para dataset especializado | 30.0% |
| `--anchor-pct` | % tokens para anchor datasets | 70.0% |
| `--report` | Ruta para report de composición | Opcional |

---

## 6. CONFIGURACIÓN DETALLADA

### 6.1 Config de Anchors (`configs/stage_3_curation/anchors.yaml`)

```yaml
anchors:
  - hf_id: "Salesforce/xlam-function-calling-60k"
    split: "train"
    format: "alpaca"
    token_budget_pct: 30.0

  - hf_id: "FineTome-100k"
    split: "train"
    format: "sharegpt"
    token_budget_pct: 40.0

  - hf_id: "Magicoder"
    split: "train"
    format: "sharegpt"
    token_budget_pct: 30.0
```

### 6.2 Config de Backtracking Alignment (`configs/stage_3_curation/backtracking_alignment.yaml`)

Este archivo configura el Stage 1.5 (Backtracking Alignment), un proceso adicional que reescribe los think blocks:

```yaml
# --- Filtering ---
max_tokens: 4000                    # Descartar registros con >4000 tokens
excluded_types:
  - theory                          # Tipos excluidos

# --- Inference (vLLM) ---
vllm_api_url: "http://localhost:8000/v1"
vllm_model: "qwen3-30b-a3b-thinking-fp8"
temperature: 0.6
max_generation_tokens: 3000

# --- Pipeline ---
batch_size: 10                      # Intervalo de logging
seed: 42
workers: 8                          # Concurrency (asyncio.Semaphore)

# --- Governance context ---
gap_dir: "data/Gap"
governance_context_chars: 5200

# --- Language ---
language: "Spanish"
```

---

## 7. ESTADISTICAS DE CURACIÓN

El pipeline genera automáticamente un reporte con las siguientes métricas:

### 7.1 Formato del Reporte

```json
{
  "timestamp": "2026-03-01T12:00:00Z",
  "total_input": 19732,
  "removed": {
    "exact_duplicates": 127,
    "nemo_filtered": 1245,
    "invalid_syntax": 234,
    "shallow_thinking": 456,
    "meta_speech": 89,
    "low_ldi": 321,
    "low_quality_score": 678,
    "semantic_duplicates": 234,
    "total": 3384
  },
  "total_output": 16348,
  "retention_pct": 82.85
}
```

### 7.2 Filtros Aplicados

| Fase | Filtro | Criterio |
|------|--------|----------|
| 0 | Exact Dedup | SHA-256 hash igual |
| 1 | Word Count | <20 palabras |
| 1 | Symbols Ratio | >50% símbolos |
| 1 | Non-Alpha Ratio | >65% caracteres no alfanuméricos |
| 1 | URL Ratio | >30% URLs |
| 1 | Punctuation | >99% sin punto final |
| 1 | Boilerplate | >85% texto genérico |
| 1 | Repeated Lines | >90% líneas repetidas |
| 1 | N-grams | >35% n-grams repetidos |
| 2 | Syntax Check | Python syntax inválido |
| 2 | Think Depth | <100 chars en `<think>` |
| 2 | LDI Ratio | <0.02 (Logic Density Index) |
| 2 | Meta Speech | Reasoning con lenguaje de auditoría |
| 3 | MinHash-LSH | Similaridad >0.85 |
| 3 | Quality Score | Heuristic quality <0.50 |

---

## 8. PIPELINE DE BACKTRACKING ALIGNMENT (STAGE 1.5)

El Stage 1.5 es un proceso complementario que reescribe los think blocks para incluir patrones de auto-corrección.

### 8.1 Ejecución del Backtracking Rewriter

```bash
python -m src.curation.rewrite_cli \
    --input data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl \
    --output data/synthetic/v11_backtracking_aligned_20260301_120000.jsonl \
    --config configs/stage_3_curation/backtracking_alignment.yaml \
    --audit-dir data/audit
```

### 8.2 Estrategias de Rewrite

| Estrategia | Condición | Descripción |
|------------|-----------|-------------|
| `full_backtracking` | `legacy_detected=True` | Simular impulso legacy → autocorrección |
| `trace_reconstruction` | `gold_injected=True` | Reconstruir reasoning trace para código gold |
| `error_first` | `example_type=error_recovery` | Identificar error → wrong fix → correct fix |
| `contrast_backtracking` | `example_type=contrast` | Presentar old vs new → rechazar old |
| `pass_through` | default | Mantener think original |
| `skip` | `example_type in excluded` | No procesar el registro |

### 8.3 Patrón de Backtracking

El rewriter genera patrones de reasoning como:

```
1. LEGACY IMPULSE: "Mi primer instinto es usar hass.data..."
2. SELF-EVALUATION: "Espera, esto viola la regla de HA 2026..."
3. BACKTRACKING: "Necesito usar entry.runtime_data en su lugar..."
4. MODERN RESOLUTION: "Plan final usando la API moderna..."
```

---

## 9. FLUJO COMPLETO DE EJECUCIÓN

### 9.1 Script Completo

```bash
#!/bin/bash
# Stage 3 Curation Pipeline - Ejecución completa

set -e

# 1. Arrancar container de curación
cd /mnt/bunker_data/ai/data_factory/deploy/docker
docker compose up -d curator

# 2. Ejecutar Phase 0 - Exact Dedup (local)
cd /mnt/bunker_data/ai/data_factory
python -m src.curation.curator_cli \
    --input data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl \
    --output data/curated/phase0_dedup.jsonl \
    --exact-dedup \
    --apply

# 3. Ejecutar Phase 1 - NeMo Filter (dentro del container)
docker exec -it aegf_curator bash -c "
    cd /workspace && \
    python -m src.curation.curator_cli \
        --input data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl \
        --output data/curated/phase1_filter.jsonl \
        --filter \
        --apply
"

# 4. Ejecutar Phase 2 - Structural Filter (local)
python -m src.curation.curator_cli \
    --input data/curated/phase1_filter.jsonl \
    --output data/curated/phase2_structural.jsonl \
    --structural \
    --apply

# 5. Ejecutar Phase 3 - Semantic Dedup (local)
python -m src.curation.curator_cli \
    --input data/curated/phase2_structural.jsonl \
    --output data/curated/phase3_semantic.jsonl \
    --dedup \
    --apply

# 6. Ejecutar Mix-Datasets (local)
python -m src.curation.curator_cli \
    --mix-datasets \
    --specialized-jsonl data/curated/phase3_semantic.jsonl \
    --anchor-configs configs/stage_3_curation/anchors.yaml \
    --output-jsonl data/mixed/v11_mixed_20260301_120000.jsonl \
    --seed 42 \
    --specialized-pct 30.0 \
    --anchor-pct 70.0 \
    --report data/reports/composition_report.json

echo "Stage 3 curation completed successfully!"
```

---

## 10. ARCHIVOS Y ESTRUCTURA DEL PROYECTO

```
/mnt/bunker_data/ai/data_factory/
├── src/
│   └── curation/
│       ├── curator_cli.py              ← CLI principal
│       ├── curator_pipeline.py         ← Pipeline core
│       ├── backtracking_rewriter.py    ← Stage 1.5 rewriter
│       ├── backtracking_config.py      ← Config dataclass
│       ├── backtracking_helpers.py     ← Helpers
│       ├── anchor_dataset_downloader.py ← Download anchors
│       ├── dataset_mixer.py            ← Mixing logic
│       ├── dedup_filter.py             ← MinHash-LSH
│       ├── quality_filter.py           ← Structural filters
│       └── format_normalizer.py        ← Normalization
│
├── configs/
│   └── stage_3_curation/
│       ├── anchors.yaml                ← Anchor configs
│       ├── backtracking_alignment.yaml ← Backtracking config
│       └── prompts/
│           └── user.yaml               ← Prompt templates
│
├── docs/
│   └── specs/
│       └── stage_1_5_backtracking_alignment.md  ← Doc completa
│
├── data/
│   ├── synthetic/                      ← Input
│   ├── curated/                        ← Output phase 0-2
│   ├── mixed/                          ← Output mix-datasets
│   └── reports/                        ← Stats reports
│
└── deploy/
    └── docker/
        ├── docker-compose.yaml         ← Container definition
        └── .env                        ← Env variables
```

---

## 11. RESUMEN DE ACCIONES

### 11.1 Comandos Principales

1. **Curación completa:**
   ```bash
   python -m src.curation.curator_cli --input X --output Y --exact-dedup --filter --structural --dedup --apply
   ```

2. **Mix de datasets:**
   ```bash
   python -m src.curation.curator_cli --mix-datasets --specialized-jsonl X --anchor-configs Y --output-jsonl Z
   ```

3. **Backtracking Alignment:**
   ```bash
   python -m src.curation.rewrite_cli --input X --output Y --config Z
   ```

### 11.2 Container Deployment

```bash
cd deploy/docker && docker compose up -d curator
docker exec -it aegf_curator bash
```

---

## 12. NOTAS IMPORTANTES

1. **Phase 1 requiere container**: El NeMo Curator pipeline solo funciona dentro del container `aegf_curator`
2. **Dry-run mode**: Sin `--apply` el pipeline solo simula sin escribir
3. **Sample mode**: `--sample N` procesa solo los primeros N registros para testing
4. **Reports automáticos**: El pipeline genera reports JSON en `data/reports/`
5. **Backtracking Alignment** es opcional pero recomendado para mejorar la calidad del reasoning

---

**Documento generado:** 2026-04-01
**Versión:** Stage 3 v1.0
**Estado:** Documentación completa
