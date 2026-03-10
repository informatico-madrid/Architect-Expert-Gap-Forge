# Tasks: Stage 1 — Refactor (Language Abstraction)

Feature: Stage 1 — Discovery, Processor y Master Documents (refactor brownfield)
Plan: specs/001-stage1-discovery/plan.md
Spec: specs/001-stage1-discovery/spec.md

---

Phase 1 — Setup

- [x] T001 [P] Crear paquete de extractores y archivo de inicialización en `src/utils/extractors/__init__.py`

Phase 2 — Foundational (bloqueantes; seguir TDD: tests antes de implementación)

- [x] T002 Crear prueba unitaria que defina el contrato del adapter: `tests/unit/test_extractor_adapter_contract.py` (falla esperado)
- [x] T003 Implementar `ExtractorAdapter` y tipos en `src/utils/extractors/base.py` para satisfacer `tests/unit/test_extractor_adapter_contract.py`
- [x] T004 Crear prueba unitaria para `python_ast_adapter`: `tests/unit/test_python_ast_adapter.py` (uso de fixtures con archivos Python de ejemplo)
- [x] T005 Implementar `src/utils/extractors/python_ast_adapter.py` (portar la lógica actual de `processor._extract_local_imports`) para pasar `tests/unit/test_python_ast_adapter.py`
- [x] T006 Crear prueba unitaria para la fábrica de adapters: `tests/unit/test_extractors_factory.py` (espera `get_adapter('homeassistant')`)
- [x] T007 Implementar `src/utils/extractors/factory.py` con `get_adapter(profile: str) -> ExtractorAdapter` (importación perezosa)
- [x] T008 Crear prueba de integración que verifique que `processor` usa el adapter para extraer dependencias: `tests/integration/test_processor_adapter_integration.py`
- [x] T009 Refactorizar `src/discovery/processor.py` para usar `adapter.parse_file()` / `adapter.extract_dependencies()` y añadir manejo `on_parse_error` (política por defecto: marcar `needs_manual_review` y abortar el repo) — archivo: `src/discovery/processor.py`

Phase 3 — User Stories (en prioridad)

User Story 1 — Ingestar repositorios (Priority: P1)

- [x] T010 [US1] Crear prueba unitaria `tests/unit/test_ingestor_profile_filter.py` que valide que `ingestor` aplica filtros del `profile` (dry-run)
- [x] T011 [US1] Actualizar `src/discovery/ingestor.py` y `DiscoveryConfig` para aceptar `profile` y aplicar filtros por `extensions`/`ignored_paths` — archivo: `src/discovery/ingestor.py`

User Story 2 — Emitir paquetes por módulo (Priority: P1)

- [x] T012 [US2] Crear prueba unitaria `tests/unit/test_processor_module_discovery_manifest.py` que defina comportamiento esperado para `strategy: manifest`
- [x] T013 [US2] Implementar soporte `strategy: manifest` en `src/discovery/processor.py` (leer manifestos/anchors)
- [x] T014 [US2] Crear prueba unitaria `tests/unit/test_processor_module_discovery_directory_and_manual.py` que cubra `strategy: directory` y `strategy: manual_mapping` con `overrides`
- [x] T015 [US2] Implementar `directory` y `manual_mapping` strategies y `overrides` en `src/discovery/processor.py`
- [x] T016 [US2] Crear prueba de integración `tests/integration/test_processor_emits_bundles_with_arch_header.py` que verifique que los bundles `.txt` contienen `[ARCH_HEADER]` con `MODULE`, `DEPENDENCIES`, etc.

User Story 3 — Carga dinámica de Master Documents (Priority: P2)

- [x] T017 [US3] Crear prueba unitaria `tests/unit/test_load_master_docs_profile.py` que falle cuando falta un `master_doc` obligatorio
- [x] T018 [US3] Actualizar `src/factory/production_v11.py` para exponer `load_master_docs(gap_dir: Path, profile: str)` y leer `configs/stage_1_discovery/master_docs_map.yaml` — archivo: `src/factory/production_v11.py`

Final Phase — Polish & Cross-cutting

- [x] T019 [P] Añadir ejemplos versionados: `configs/stage_1_discovery/examples/homeassistant.yaml` y `configs/stage_1_discovery/examples/php_hexagonal.yaml` con `on_parse_error: abort` por defecto
- [x] T020 Crear pruebas unitarias para validar políticas `on_parse_error` (`tests/unit/test_parse_error_policy.py`)
- [x] T021 Ejecutar test suite completa y corregir fallos: `pytest tests/unit tests/integration` (entregar logs y correcciones)
  - **Criterios de salida:** todos los tests unitarios deben pasar localmente; generar `reports/tests-report.xml` y `reports/pytest-logs.txt` adjuntos al PR.
- [x] T022 Ejecutar formateo y comprobaciones: `ruff format .` y `python scripts/check_headers.py --check`
- [x] T023 Actualizar `specs/001-stage1-discovery/quickstart.md` si cambian comandos o flags
- [x] T024 Preparar un PR draft con los cambios y artefactos — incluir: `specs/*`, `src/utils/extractors/*`, `src/discovery/processor.py` y tests
  - **Criterios de salida:** PR draft debe incluir: lista de tests que fueron migrados (resultado T031), benchmark baseline (T032), checklist de cambios y un archivo `PR_CHECKLIST.md` con pasos de verificación para reviewers.

Additional Critical Test Tasks (added to cover spec gaps)

- [x] T025 Pruebas unitarias/integración para la resiliencia Git: validar `git pull --ff-only` y la política segura de recuperación mediante `fetch`+`reset`.
  - **Política de retry:** intentar hasta **3** veces (`pull` → `fetch`+`reset`) con backoff exponencial (1s, 2s, 4s) antes de fallar.
  - **Criterios de seguridad:** aplicar `reset` solo cuando el remote contenga el commit objetivo en su historia; comprobar ancestry/commit-IDs para evitar resets destructivos.
  - **Tests:** `tests/unit/test_ingestor_git_fallback.py`, `tests/integration/test_ingestor_git_recovery.py` (escenarios: network error, diverged history, shallow clone).
- [x] T026 Hardening e implementación de la recuperación en `src/discovery/ingestor.py` con las comprobaciones listadas arriba (implementación + tests). Incluir validaciones de checksum/HEAD para abortar cuando la historia es incoherente.
- [x] T027 Tests de backoff por rate-limit: simular respuestas 403 con `X-RateLimit-Reset` y verificar sleep+retry+logs (tests/unit/test_rate_limit_backoff.py). Policy: sleep hasta `X-RateLimit-Reset + 5s`, máximo 2 reintentos por endpoint.
- [x] T028 Crear harness de integración y fixtures: conjunto referencial de **5** repositorios por `profile` en `tests/fixtures/reference_corpus/<profile>/` con `gold_dependencies.json` para medir recall.
- [x] T029 Implementar scripts de medición automática (recall/precision) y reporte para extractor (scripts/measure_recall.py, tests/integration/test_recall_harness.py). Métrica canon: `recall@N` (N=5,10) por archivo/por repositorio.
- [x] T030 Observabilidad: implementar métricas exportables (Prometheus-friendly) para `ParseError` (contador por repo/profile), latencias y tasa de archivos marcados; añadir tests que verifiquen la emisión de métricas.
 - [x] T031 Auditar tests existentes que dependen del fallback AST (p.ej. `_ast_fragment_list` fallback) y producir plan de migración (lista de tests a actualizar + cambios propuestos). Generar `specs/001-stage1-discovery/ast_fallback_audit.json` con resultados y marcar esta tarea `in-progress`.
  - **Salida (spec-only):** `specs/001-stage1-discovery/migrations/test_migration_plan.md` contiene la estrategia recomendada y plantilla de migración por test. Implementación de cambios en tests o código corresponde a otro agente.
- [x] T032 Performance: benchmarking & CI comparison — crear scripts para medir throughput (files/hour per worker), latency per-file (mean and P95) y comparar baseline vs post-refactor (scripts/benchmark/; tests/integration/test_benchmark_compare.py).

---

Dependencies (orden de completado recomendado)

- Bloqueantes iniciales: Phase 2 Foundational (T002..T009) deben completarse antes de la implementación de User Stories (T010..T018).
- Orden recomendado:
  1. T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009
  2. Luego: US1 (T010→T011) y US2 (T012→T016) en paralelo si Foundational completo
  3. Finalmente: US3 (T017→T018) y Final Phase (T019..T024)

Parallel execution examples

- Se pueden ejecutar en paralelo (por distintas personas/agentes):
  - Crear tests unitarios independientes (`T002`, `T004`, `T006`) — [P]
  - Crear adapters y fábrica (`T003`, `T005`, `T007`) — se implementan tras cada test, pero distintas implementaciones son paralelizables si no compiten por los mismos archivos.
  - US1 y US2 se pueden desarrollar en paralelo una vez que `processor` use `ExtractorAdapter` (post-T009).

Implementation strategy (MVP first)

- MVP scope (mínimo para mergeable increment):
  - Implementar `src/utils/extractors/base.py` + `python_ast_adapter` + `factory.get_adapter()` (T002..T007)
  - Refactor `processor` para usar adapter y aplicar `on_parse_error=abort` por defecto (T008..T009)
  - Crear `configs/stage_1_discovery/examples/homeassistant.yaml` y `master_docs_map.yaml` con los `master_docs` obligatorios para `homeassistant` (T019)
  - Añadir tests unitarios e integración mínima (T002, T004, T008, T016)

- Entrega incremental:
  1. Entrega: adapters básicos + processor wiring + tests verdes para homeassistant profile
  2. Añadir: `manual_mapping` y `directory` strategies, más tests
  3. Añadir: `php_hexagonal` profile y sus adapters/tests (tree-sitter/externos si se decide)

Validation criteria (por tarea)

- Cada tarea de implementación debe tener una o más pruebas que inicialmente fallen y que pasen tras la implementación (TDD). Los archivos de prueba están listados en cada tarea.
- Todas las pruebas unitarias deben pasar localmente antes de preparar el PR draft.

---

Total tasks: 31
- Tasks por user story: US1=2, US2=5, US3=2
- Paralel opportunities: tests/adapter implementation parallelization y US1/US2 después del foundational

Generated by: copilot agent (plan: specs/001-stage1-discovery/plan.md)

## Migration: High-priority test checklists

Las siguientes entradas derivan de specs/001-stage1-discovery/migrations/test_migration_plan.md y sirven para tracking TDD (actualizar cada ítem cuando el test sea modificado y las correcciones implementadas).

- [ ] `tests/test_production_v11.py` — Migrar a ParseError-first.
  - Paso 1: Actualizar el test para esperar `ParseError` (ver plantilla en `migrations/test_migration_plan.md`) y ejecutar `pytest`.
  - Paso 2: Implementador adapta el adapter/`production_v11` para lanzar `ParseError` y pasar la prueba.
  - Paso 3: Añadir nota en la PR enlazando FR-006.

- [ ] `tests/test_production_v11_helpers.py` — Migrar a ParseError-first.
  - Paso 1: Actualizar el test para usar `pytest.raises(ParseError)`.
  - Paso 2: Ejecutar pruebas locales.
  - Paso 3: Implementador hace cambios en `_ast_fragment_list` o adapter.

- [ ] `tests/test_model_evaluator_integration_paths.py` — Revisar y migrar AST-related.
  - Paso 1: Identificar sub-tests que llaman a `_ast_fragment_list`.
  - Paso 2: Aplicar patrón ParseError-first a esos sub-tests.
  - Paso 3: Documentar cambios.

- [ ] `tests/test_sampling.py` — Revisar y clasificar.
  - Paso 1: Confirmar si depende de AST fallback.
  - Paso 2: Si no, dejar y marcar como no-ast.
  - Paso 3: Si sí, migrar según plantilla.

- [ ] `tests/test_model_evaluator_extended_paths.py` — Revisar y clasificar.
  - Paso 1: Extraer tests AST-specific.
  - Paso 2: Migrar AST-cases a ParseError-first.
  - Paso 3: Documentar y parametrizar si es necesario.

Referencias:

- Migration plan: specs/001-stage1-discovery/migrations/test_migration_plan.md
- Audit report: specs/001-stage1-discovery/ast_fallback_audit.json
