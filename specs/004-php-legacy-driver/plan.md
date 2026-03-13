# Implementation Plan: PHPLegacyDriver (Regex-Based Extractor)

**Branch**: `004-php-legacy-driver` | **Date**: 2026-03-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-php-legacy-driver/spec.md`

## Summary

Implementar un driver regex-based para extraer fragmentos de código PHP legacy procedural (osCommerce, WordPress, ZenCart, Magento, etc.) y generar bundles `.txt` compatibles con el pipeline Stage 2. El driver implementa el protocolo `ExtractorAdapter`, fragmenta por bloques funcionales heurísticos (funciones, switch/case, bloques PHP), aplica etiquetado semántico en 6 categorías, y genera secciones `[LEGACY_SIGNATURES]` con Anti-Patterns Mapping. Stage 2 se extiende con un parser de secciones genérico y un Extension Mapper para routing por lenguaje. Templates de prompt dedicados generan output en 3 secciones (DEBT_DIAGNOSTIC, MODERN_PROPOSAL, MAPPING_LOGIC) orientados a modernización PHP → Symfony hexagonal.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: re (stdlib), pathlib (stdlib), dataclasses (stdlib), pydantic (existente en proyecto), concurrent.futures (stdlib — ProcessPoolExecutor + ThreadPoolExecutor)
**Storage**: Filesystem local — bundles `.txt` en `data/outputs/`, repositorios fuente en `data/raw/multi_legacy/`
**Testing**: pytest con typed fixtures, pytest-cov ≥90%
**Target Platform**: Linux server (local, soberanía de datos), AMD Threadripper (multi-core)
**Project Type**: Pipeline library (extensión de pipeline AEGF existente)
**Performance Goals**: <5 seg/archivo PHP de 2000+ líneas; saturar cores del Threadripper vía ProcessPoolExecutor
**Constraints**: Sin dependencias externas de network, sin parser AST de PHP, regex-only, GIL bypass vía multiprocessing
**Scale/Scope**: 7 plataformas legacy en `data/raw/multi_legacy/`, ~miles de archivos `.php`

## Parallel IO Architecture

El procesamiento de ~miles de archivos requiere orquestación explícita en dos etapas para saturar el Threadripper:

```
Stage 1 — IO-bound (ThreadPoolExecutor, max_workers=32)
  Path.rglob("*.php") → ThreadPoolExecutor.map(read_file) → dict[Path, str]

Stage 2 — CPU-bound (ProcessPoolExecutor, max_workers=os.cpu_count())
  dict[Path, str] → ProcessPoolExecutor.submit(process_php_file) → list[PhpFragment]

Stage 3 — IO-bound (ThreadPoolExecutor, max_workers=16)
  list[PhpFragment] → ThreadPoolExecutor.map(write_bundle) → .txt files
```

**Worker constraint**: `process_php_file(path: Path, content: str) -> list[PhpFragment]` debe ser una función top-level importable en `php_fragmenter.py` (no lambda, no closure) para ser serializable por `pickle` en el IPC de `ProcessPoolExecutor`.

**Chunksize**: Para repos de 1000+ archivos, usar `chunksize=50` en `ProcessPoolExecutor.map()` para reducir overhead de serialización IPC.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| II. Testing ≥90% coverage | PASS | Tests unitarios + integración para driver, fragmenter, parser. Fixtures por plataforma. |
| III. Strict typing | PASS | Todas las entidades son frozen dataclasses o Pydantic models. Protocol existente se reutiliza. |
| III. Immutability | PASS | PhpFragment, LegacySignature, PlatformProfile son frozen dataclasses. |
| III. No import-time side effects | PASS | Patrones se cargan lazy desde configuración, no al importar. |
| III. Logging | PASS | `logger = logging.getLogger(__name__)` por módulo, lazy formatting. |
| IV. Strategy + Router | PASS | Extension Mapper en `get_v2_fragments()` es un Router pattern. Adapters son Strategy. |
| IV. Prompt externalization | PASS | Templates PHP en `configs/stage_2_factory/taxonomy/` — misma arquitectura que Python/HA. |
| IV. Batch operations | PASS | Procesamiento por repositorio completo, no archivo por archivo. |
| IV. SRP & module size | PASS | Módulos separados: adapter, fragmenter, signatures, graph, profiles. |
| V. Header policy | PASS | Todos los archivos `.py` nuevos incluyen header AEGF. |
| VII. No silent failures | PASS | ParseError explícito, `needs_manual_review.json` para archivos problemáticos. |
| VIII. YAGNI | PASS | Solo lo que la spec define — sin AST PHP, sin ejecución runtime, sin modernización automática. |

**GATE RESULT: ALL PASS** — No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-php-legacy-driver/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── bundle-format.md # Bundle .txt contract for PHP
│   └── prompt-schema.md # Teacher output 3-section schema
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── utils/extractors/
│   ├── base.py                    # ExtractorAdapter Protocol (existing)
│   ├── factory.py                 # Adapter registry (extend with php_legacy)
│   ├── python_ast_adapter.py      # Existing Python adapter
│   └── php_legacy_adapter.py      # NEW: PhpLegacyAdapter
├── discovery/
│   ├── processor.py               # MODIFY: add PHP module discovery strategy
│   ├── php_fragmenter.py          # NEW: heuristic block fragmenter
│   ├── php_signatures.py          # NEW: regex pattern engine + categories
│   ├── php_include_graph.py       # NEW: include/require dependency graph
│   └── php_platform_profiles.py   # NEW: platform detection + profile patterns
└── factory/
    └── production_v11.py          # MODIFY: Extension Mapper + generic section parser

configs/
└── stage_2_factory/
    ├── taxonomy/
    │   └── php_legacy/
    │       ├── taxonomy.yaml              # NEW: PHP prompt templates
    │       ├── master_symfony_hex.md       # NEW: Symfony hexagonal doctrine
    │       └── snippets/                  # NEW: per-platform anti-pattern maps
    │           ├── oscommerce.md
    │           ├── wordpress.md
    │           ├── zencart.md
    │           ├── openmage.md
    │           ├── prestashop.md
    │           ├── codeigniter.md
    │           ├── suitecrm.md
    │           └── generic_php.md
    └── prompts/                           # (if taxonomy uses separate files)

tests/
├── unit/
│   ├── test_php_legacy_adapter.py         # NEW
│   ├── test_php_fragmenter.py             # NEW
│   ├── test_php_signatures.py             # NEW
│   ├── test_php_include_graph.py          # NEW
│   ├── test_php_platform_profiles.py      # NEW
│   └── test_extension_mapper.py           # NEW
├── integration/
│   ├── test_php_processor_bundles.py      # NEW
│   └── test_php_stage2_roundtrip.py       # NEW
└── fixtures/
    └── php_legacy/                        # NEW
        ├── oscommerce_categories.php      # Representative fixture
        ├── wordpress_ajax_actions.php     # Representative fixture
        └── zencart_customers.php          # Representative fixture
```

**Structure Decision**: Extensión del proyecto existente — nuevos módulos en `src/discovery/` y `src/utils/extractors/`, modificaciones quirúrgicas en `processor.py` y `production_v11.py`. Sin nuevos packages ni directorios de alto nivel.

## Complexity Tracking

No aplica — Constitution Check passed sin violations.
