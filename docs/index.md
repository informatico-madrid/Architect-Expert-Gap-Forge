# AEGF Project Documentation Index

> **Generated:** 2026-04-21  
> **Project:** data_factory (AEGF — Architect-Expert-Gap-Forge)  
> **Scan Level:** Exhaustive  
> **Project Type:** Python backend / data pipeline / CLI tool  
> **Parts:** 1 (monolith)

---

## Project Overview

AEGF es una fábrica de datos sintéticos de alto rendimiento diseñada para resolver el **problema del Knowledge Cutoff** en Large Language Models. Proporciona una pipeline modular de 6 etapas para extraer "Gold Code" de repositorios de producción, inyectar "API Deltas" desde changelogs, y sintetizar trayectorias "Platinum-Tier" para fine-tuning especializado.

**Propósito principal:** Capturar conocimiento reciente de APIs, migraciones legacy→modern, y arquitecturas domain-specific (ej. Home Assistant 2026) para entrenar LLMs con datos de alta fidelidad.

---

## Architecture: 6-Stage Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Stage 1    │───>│  Stage 2     │───>│  Stage 3        │
│ Discovery   │    │ Factory      │    │ Merger/Repair   │
│ (Ingest)    │    │ (Synthesis)  │    │ (Merge DNA)     │
└─────────────┘    └──────────────┘    └─────────────────┘
       │                   │                    │
       v                   v                    v
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Stage 4    │    │  Stage 5     │    │  Stage 6        │
│ Training    │<───│  Evaluation  │<───│  Calibration    │
│ (SFT/LoRA)  │    │ (Scoring)    │    │ (Gap Analysis)  │
└─────────────┘    └──────────────┘    └─────────────────┘
```

| Stage | Module | Purpose |
|-------|--------|---------|
| 1 | `src/discovery/` | Ingestión de repositorios, fragmentación por lenguaje |
| 2 | `src/factory/` | Síntesis de datos sintéticos con inyección de conocimiento |
| 3 | `src/merger/` | Fusión y reparación de DNA de datos |
| 4 | `src/research/` + `src/training/` | Orquestación de experimentos y validación de training |
| 5 | `src/audit/` | Evaluación, scoring, calibration |
| 6 | `src/audit/calibration.py` | Análisis de gaps y calibración final |

---

## Source Code Structure

### `src/` — Módulos Principales

| Módulo | Archivos | Descripción |
|--------|----------|-------------|
| [`audit/`](src/audit/) | 13 archivos | Calibration, evaluación, scoring, exam generation |
| [`curation/`](src/curation/) | 12 archivos | Dataset curation, dedup, quality filtering, backtracking |
| [`discovery/`](src/discovery/) | 9 archivos | Stage 1: repo ingestion, PHP fragmentation, metadata |
| [`export/`](src/export/) | 2 archivos | ChatML export, frontend taxonomy prompts |
| [`factory/`](src/factory/) | 14 archivos | Stage 2: synthetic data factory, agentic teacher |
| [`merger/`](src/merger/) | 13 archivos | Stage 3: merge pipelines, DNA repair, fusion |
| [`quantizer/`](src/quantizer/) | 1 archivo | FP8 quantization for Blackwell (sm_120) |
| [`research/`](src/research/) | 4 archivos | Experiment orchestration, batch generation |
| [`schemas/`](src/schemas/) | 3 archivos | Common data schemas, converters |
| [`training/`](src/training/) | 1 archivo | Training config validation |
| [`utils/`](src/utils/) | 8+ archivos | Cross-cutting utilities, extractors |

### `src/utils/extractors/` — Adapter Pattern

| Adapter | Archivo | Lenguaje |
|---------|---------|----------|
| `JinjaAdapter` | `jinja_adapter.py` | Jinja2 templates |
| `MarkdownAdapter` | `markdown_adapter.py` | Markdown |
| `PHPLegacyAdapter` | `php_legacy_adapter.py` | PHP (legacy) |
| `PythonASTAdapter` | `python_ast_adapter.py` | Python (AST) |
| `TypeScriptAdapter` | `typescript_adapter.py` | TypeScript |
| `YAMLAdapter` | `yaml_adapter.py` | YAML |

---

## Test Structure

### `tests/` — Suite de Pruebas

| Directorio | Contenido |
|------------|-----------|
| `tests/unit/` | Tests unitarios puros (sin I/O) |
| `tests/integration/` | Tests de integración cross-module |
| `tests/e2e/` | Tests end-to-end |
| `tests/audit/` | Tests específicos del módulo audit |
| `tests/curation/` | Tests específicos del módulo curation |
| `tests/discovery/` | Tests específicos del módulo discovery |
| `tests/factory/` | Tests específicos del módulo factory |
| `tests/training/` | Tests específicos del módulo training |
| `tests/fixtures/` | Datos de prueba, mocks, samples |

**Cobertura objetivo:** >=85% para módulos trackeados  
**Módulos trackeados:** `src/audit`, `src/utils`, `src/factory`, `src/curation`, `src/discovery`

---

## Configuration Structure

### `configs/` — Configuración Externa

| Ruta | Propósito |
|------|-----------|
| `configs/prompts/` | System prompts para backtracking y reconstruction |
| `configs/stage_1_discovery/` | Config de discovery (perfiles, repos estáticos) |
| `configs/stage_2_factory/` | Taxonomía y prompts de factory |
| `configs/stage_4_training/` | Config de training (axolotl, deepspeed) |
| `configs/stage_5_evaluation/` | Config de evaluación |
| `configs/stage_6_calibration/` | Config de calibración |

### Archivos de Configuración Clave

| Archivo | Propósito |
|---------|-----------|
| `pyproject.toml` | Build, test, coverage, ruff config |
| `requirements.txt` | Runtime dependencies |
| `requirements-dev.txt` | Dev dependencies |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `pyrightconfig.json` | Type checking config |
| `.env.example` | Template de variables de entorno |

---

## Specifications

### `specs/` — Especificaciones de Features

| Spec | Estado | Descripción |
|------|--------|-------------|
| `000-proyecto-actual/` | Base | Spec actual del proyecto |
| `001-stage1-discovery/` | ✅ | Stage 1 discovery implementation |
| `002-ralph-worktree/` | ✅ | Ralph worktree integration |
| `003-monolith-modules/` | ✅ | Monolith module refactoring |
| `004-php-legacy-driver/` | ✅ | PHP legacy driver |
| `005-inference-calibration/` | ✅ | Inference calibration |
| `006-project-maintenance/` | ✅ | Project maintenance |
| `008-fix-ingestor-cli-execution/` | ✅ | Fix ingestor CLI |
| `011-fix-failing-tests/` | ✅ | Fix failing tests |
| `012-mejorar-cobertura-code/` | ✅ | Improve code coverage |
| `013-ingestor-yaml-tests/` | ✅ | Ingester YAML tests |
| `014-rich-cli-output/` | ✅ | Rich CLI output |
| `frontend-discovery-enhancement/` | 🔄 | Frontend discovery enhancement |
| `module-discovery-auto/` | 🔄 | Module discovery auto |
| `yaml-adapter/` | 🔄 | YAML adapter spec |

---

## BMAD Workflow Artifacts

### `_bmad/` — Configuración BMAD

| Módulo | Config |
|--------|--------|
| `bmb/` | Module builder |
| `bmm/` | Module manager |
| `cis/` | Creative innovation system |
| `core/` | Core workflow |
| `tea/` | Test architecture |

### `_bmad-output/` — Artefactos Generados

| Archivo | Descripción |
|---------|-------------|
| `project-context.md` | Contexto de proyecto para agentes IA |

---

## Deployment

### `deploy/` — Configuración de Despliegue

| Archivo | Propósito |
|---------|-----------|
| `deploy/.env.example` | Template de entorno para deploy |
| `deploy/docker/docker-compose.yaml` | Docker Compose para orchestración |
| `deploy/docker/Dockerfile.curator` | Dockerfile para módulo curator |

---

## Diagnostics

### `diagnose/` — Scripts de Diagnóstico

| Script | Propósito |
|--------|-----------|
| `dataset_health_check.py` | Health check de datasets |
| `distill_v11.py` | Distillation v11 |
| `aegf_dataset_audit.py` | Auditoría de datasets AEGF |
| `compare_ldi_versions.py` | Comparación de versiones LDI |

---

## Key Architectural Patterns

### 1. Strategy + Router
Los backends de inferencia están detrás de una interfaz strategy, seleccionada por un router.

### 2. Profile-Based Discovery (Stage 1)
El motor de discovery usa perfiles YAML-driven para soporte multi-lenguaje:
- `homeassistant` → Python (PythonASTAdapter)
- `php_hexagonal` → PHP (PHPExtractorAdapter)

### 3. Extractor Adapter Pattern
Extensible via factory pattern en `src/utils/extractors/factory.py`.

### 4. Prompt Externalization
Todos los prompts viven en `configs/`, gestionados por `PromptManager`.

### 5. Immutability by Default
Data records son frozen dataclasses o pydantic models con `frozen=True`.

---

## Commands Reference

```bash
# Test suite
make test

# Coverage
make coverage

# Linting
ruff check .

# Type checking
pyright

# Install
pip install -e ".[dev]"
```

---

## Governance Documents

| Documento | Ubicación |
|-----------|-----------|
| Constitution | `.specify/memory/constitution.md` |
| Architectural Gold Standard | `.github/agents/AEGF.agent.md` |
| Project Operations | `AGENTS.md` |
| Methodology | `docs/METHODOLOGY.md` |
| Architecture | `docs/AGENTS_ARCHITECTURE.md` |

---

## Environment

- **Runtime:** Python >=3.12
- **Container:** Home Assistant Container (sin Supervisor)
- **Vector DB:** Qdrant (MCP integration)
- **LLM Backends:** Google Gemini (optional), vLLM/OpenAI (primary)
