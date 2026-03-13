# Implementation Plan: PHPLegacyDriver (filled)

**Branch**: `004-php-legacy-driver` | **Date**: 2026-03-13 | **Spec**: specs/004-php-legacy-driver/spec.md
**Input**: Feature specification from `/specs/004-php-legacy-driver/spec.md`

## Summary

Implementación del `PHPLegacyDriver`: extractor regex-based para repositorios PHP legacy (osCommerce, WordPress, ZenCart, OpenMage, PrestaShop, CodeIgniter, SuiteCRM). Produce bundles `.txt` compatibles con Stage 2 (`parse_bundle()` y `get_v2_fragments()`), añade `[LEGACY_SIGNATURES]`, `[INCLUDE_GRAPH]`, y `PREAMBLE_REF` (SHA-256). Diseño dirigido a: Python 3.11, `ProcessPoolExecutor` (CPU-bound) + `ThreadPoolExecutor` (IO), `FastBraceScanner` para brace-matching, `MappingProxyType` para inmutabilidad runtime de `PlatformProfile`, y templates `php_legacy` para Stage 2 prompts.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: Python standard library (concurrent.futures, dataclasses, typing, pathlib, re, hashlib), `pytest` for tests; optional local vLLM/judge for Validation Judge (sampling).
**Storage**: Local filesystem — `data/raw/`, `data/outputs/*_bundles/`, `needs_manual_review.json`, bundle cache for preambles.
**Testing**: `pytest` with unit/integration fixtures under `tests/`; coverage target ≥90% for modified modules.
**Target Platform**: Linux server (CI and developer workstations).
**Project Type**: Library/CLI extension of existing AEGF pipeline (no new top-level service).
**Performance Goals**: SC-001 — procesar un archivo PHP representativo (≥2000 líneas) en <5s; Stage 2 parseabilidad 100% de bundles; Validation Judge sampling latency <500ms.
**Constraints**: Offline-only processing (no external network calls), no compiled native deps, minimal third-party packages, strict typing and immutability by default (AEGF constitution).
**Scale/Scope**: Soportar los 8 repositorios en `data/raw/multi_legacy/` (incluyendo osCommerce Phoenix/gburton), procesar hasta miles de archivos (cada uno hasta 10k líneas) en paralelo usando todas las CPUs disponibles.

## Constitution Check

*GATE: Debe pasar antes de Phase 0 research. Se vuelve a comprobar tras Phase 1 design.*

Checks (derived from `.specify/memory/constitution.md`):

- **Strict typing & dataclasses**: DESIGN follows `@dataclass(slots=True, frozen=True)` for entities (`PhpFragment`, `LegacySignature`, `IncludeGraph`, `PlatformProfile`) — PASS.
- **Immutability**: `PlatformProfile.signature_patterns` coerced to `MappingProxyType` in `__post_init__` — PASS.
- **No import-time side-effects**: Modules designed as pure functions/classes; worker functions top-level for `ProcessPoolExecutor` — PASS (implementation MUST follow pattern).
- **Logging**: Use per-module `logger = logging.getLogger(__name__)` and lazy formatting — ADVISE (follow in code).
- **Testing & Coverage**: `pytest` required; CI rule: new modules to reach ≥90% coverage — gating requirement (enforced at PR time) — PASS (plan includes tests/fixtures).
- **Header policy**: New Python files must include project header — NOTE for implementers.

Result: No constitution violations identified that would block Phase 0/1. Any deviation (e.g., adding a compiled dependency) must be justified in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-php-legacy-driver/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── bundle-format.md
│   └── prompt-schema.md
├── checklists/
└── tasks.md
```

### Source Code (repository layout for this feature)

```text
src/
├── discovery/
│   ├── metadata_enricher.py        # RepoProcessor (Stage 1) — add directory_scan strategy
│   ├── php_fragmenter.py          # NEW — heuristic fragmenter + FastBraceScanner
│   ├── php_signatures.py          # NEW — legacy signature regex engine
│   ├── php_include_graph.py       # NEW — include/require graph builder
│   └── php_platform_profiles.py   # NEW — PlatformProfile registry (MappingProxyType)
├── utils/
│   └── extractors/
│       ├── base.py                # ExtractorAdapter protocol (existing)
│       ├── factory.py             # _ADAPTER_REGISTRY (register php_legacy)
│       └── php_legacy_adapter.py  # NEW — implements ExtractorAdapter
├── factory/
│   ├── fragment_extractor.py      # parse_bundle(), get_v2_fragments() (Extension Mapper)
│   ├── pipeline_runner.py         # pipeline orchestration (Stage 2)
│   └── prompt_builder.py          # build_system_with_blueprint() (php templates)
tests/
├── fixtures/php_legacy/           # oscommerce, wordpress, zencart fixtures
├── unit/
│   ├── test_php_fragmenter.py
│   └── test_php_legacy_adapter.py
└── integration/
    └── test_php_processor_bundles.py
```

**Structure Decision**: Extensión del proyecto existente en `src/discovery/` y `src/utils/extractors/`. Mínimas modificaciones en `src/discovery/metadata_enricher.py` (añadir `directory_scan` y wiring de profile), y en `src/factory/fragment_extractor.py` (Extension Mapper para `.php`). No nuevos paquetes de alto nivel ni binarios nativos.

## Complexity Tracking

No constitution violations identified that require justification. If a native dependency or external parser is proposed later, record a justification here and obtain approval.

