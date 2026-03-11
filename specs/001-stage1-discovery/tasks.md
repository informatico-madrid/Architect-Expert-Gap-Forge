# Tasks: Stage 1 — Refactor (Language Abstraction)

Feature: Stage 1 — Discovery, Processor y Master Documents (refactor brownfield)
Plan: specs/001-stage1-discovery/plan.md
Spec: specs/001-stage1-discovery/spec.md

---

Phase 1 — Setup

- [x] T001 [P] Crear paquete de extractores y archivo de inicialización en `src/utils/extractors/__init__.py`

Phase 2 — Foundational (bloqueantes; seguir TDD: tests antes de implementación)

- [x] T002 Crear prueba unitaria que defina el contrato del adapter: `tests/unit/test_extractor_adapter_contract.py`
- [x] T003 Implementar `ExtractorAdapter` y tipos en `src/utils/extractors/base.py`
- [x] T004 Crear prueba unitaria para `python_ast_adapter`: `tests/unit/test_python_ast_adapter.py`
- [x] T005 Implementar `src/utils/extractors/python_ast_adapter.py` (extracción de dependencias AST-based)
- [x] T006 Crear prueba unitaria para la fábrica de adapters: `tests/unit/test_extractors_factory.py`
- [x] T007 Implementar `src/utils/extractors/factory.py` con `get_adapter(profile: str) -> ExtractorAdapter`
- [x] T008 Crear prueba de integración que verifique que `processor` usa el adapter: `tests/integration/test_processor_adapter_integration.py`
- [x] T009 Refactorizar `src/discovery/processor.py` para `on_parse_error` completo — COMPLETO:
  - [x] T009a `processor` invoca `adapter.parse_file()` / `adapter.extract_dependencies()` para archivos `.py`
  - [x] T009b Captura `ParseError` y aplica lógica básica de `skip` / `fallback`
  - [x] T009c Estadísticas `parse_errors` y `parse_errors_aborted` en `self._stats`
  - [x] T009d Política `abort` aborta el procesamiento del repositorio completo (lanza RepoAbortError)
  - [x] T009e Marcar repo/archivo como `needs_manual_review` en informe JSON persistente
  - [x] T009f Política `mark_and_continue` explícita con registro en informe (diferente de skip)

Phase 3 — User Stories (en prioridad)

User Story 1 — Ingestar repositorios (Priority: P1)

- [x] T010 [US1] Crear prueba unitaria `tests/unit/test_ingestor_profile_filter.py`
- [x] T011 [US1] Actualizar `src/discovery/ingestor.py` y `DiscoveryConfig` — COMPLETO:
  - [x] T011a `DiscoveryConfig` acepta `profile`, `profile_extensions` y `profile_ignored_paths`
  - [x] T011b Logging de filtros activos durante el descubrimiento
  - [x] T011c `_should_include_repo` y `_filter_repos` ahora filtran realmente por extensiones y paths

User Story 2 — Emitir paquetes por módulo (Priority: P1)

- [x] T012 [US2] Crear prueba unitaria `tests/unit/test_processor_module_discovery_manifest.py`
- [x] T013 [US2] Soporte `strategy: manifest` en `processor` (detección via `manifest.json` y `__init__.py`)
- [x] T014 [US2] Crear prueba unitaria `tests/unit/test_processor_module_discovery_directory_and_manual.py`
- [x] T015 [US2] Implementar `directory` y `manual_mapping` strategies — COMPLETO:
  - [x] T015a `ProcessingConfig` acepta `module_discovery_strategy` y `module_overrides`
  - [x] T015b `_discover_modules` ahora respeta el valor de `module_discovery_strategy` en runtime
  - [x] T015c `module_overrides` / `manual_module_mapping` se aplican en el flujo de descubrimiento
- [x] T016 [US2] Crear prueba de integración `tests/integration/test_processor_emits_bundles_with_arch_header.py`

User Story 3 — Carga dinámica de Master Documents (Priority: P2)

- [x] T017 [US3] Crear prueba unitaria `tests/unit/test_load_master_docs_profile.py`
- [x] T018 [US3] `production_v11.load_master_docs(gap_dir, profile)` lee `configs/stage_1_discovery/master_docs_map.yaml` y lanza `FileNotFoundError` si falta un documento obligatorio

Final Phase — Polish & Cross-cutting

- [x] T019 [P] Añadir ejemplos versionados: `configs/stage_1_discovery/examples/homeassistant.yaml` y `configs/stage_1_discovery/examples/php_hexagonal.yaml`
- [x] T020 Pruebas unitarias para políticas `on_parse_error` — COMPLETO:
  - [x] T020a `tests/unit/test_parse_error_policy.py` cubre constantes del enum, shape de `ParseError`, raise/catch en el adapter
  - [x] T020b Tests de comportamiento del `processor` ante cada política (abort de repo, `mark_and_continue`, `needs_manual_review`) — IMPLEMENTADO
- [x] T021 Ejecutar test suite completa y corregir fallos — COMPLETO:
  - [x] T021a Tests pasan: 744 passed, 1 skipped
  - [x] T021b Ruff check: All checks passed
  - [x] T021c Fixes: Removed unused imports in `python_ast_adapter.py` and fixed ambiguous variable names in `metrics.py`
- [x] T022 Ejecutar formateo y comprobaciones: `ruff format .` y `python scripts/check_headers.py --check` — COMPLETO:
  - [x] T022a ruff format: 3 files reformatted
  - [x] T022b Header check: All critical headers present
- [x] T023 Actualizar `specs/001-stage1-discovery/quickstart.md` si cambian comandos o flags — COMPLETO:
  - [x] T023a Fixed incorrect reference to `profile.extractor_adapter` -> `profile`
  - [x] T023b Added mention of php_hexagonal profile example
- [x] T024 Preparar PR draft con los cambios — COMPLETO:
  - [x] T024a PR_CHECKLIST.md actualizado con estado preciso
  - [x] T024b Test suite verificada: 744 passed, 1 skipped
  - [x] T024c Ruff format y header check pasan

Additional Critical Test Tasks

- [x] T025 Pruebas unitarias/integración para resiliencia Git — COMPLETO:
  - [x] T025a `tests/unit/test_ingestor_git_fallback.py` existe
  - [x] T025b `tests/integration/test_ingestor_git_recovery.py` existe
  - [x] T025c `_update_repo` implementa retry con backoff exponencial (1s, 2s, 4s), hasta 3 intentos
  - [x] T025d `_safe_reset` implementa fetch + `merge-base --is-ancestor` + reset + verificación de HEAD
  - [x] T025e Tests pasan: 19 passed (10 unit + 9 integration)
  - [x] T025f Ruff check: All checks passed
- [x] T026 `src/discovery/ingestor.py` implementa `_update_repo` y `_safe_reset` con validaciones de ancestry
- [x] T027 Tests de backoff por rate-limit — COMPLETO:
  - [x] T027a `tests/unit/test_rate_limit_backoff.py` cubre casos con/sin `X-RateLimit-Reset`
  - [x] T027b `_handle_backoff` implementado (lee `X-RateLimit-Reset` + 5s, duerme)
  - [x] T027c Implementado límite de 2 reintentos máximos por endpoint (`MAX_RATE_LIMIT_RETRIES = 2`, `_rate_limit_retries` dict)
- [x] T028 Crear corpus de referencia `tests/fixtures/reference_corpus/<profile>/` con `gold_dependencies.json` — COMPLETO:
  - [x] T028a Directorio `tests/fixtures/reference_corpus/homeassistant/` existe con 5 repos
  - [x] T028b Cada repo tiene `gold_dependencies.json` con dependencias esperadas
  - [x] T028c Tests T029 y T032 ejecutan correctamente con el corpus existente
- [x] T029 Scripts de medición automática recall/precision — COMPLETO:
  - [x] T029a `scripts/measure_recall.py` existe (`compute_recall_at_n`, `measure_recall_for_repo`, `measure_recall_for_profile`)
  - [x] T029b `tests/integration/test_recall_harness.py` existe con estructura de tests
  - [x] T029c Corpus de referencia disponible — tests pasan (5 passed)
- [x] T030 Observabilidad — COMPLETO:
  - [x] T030a `src/utils/metrics.py` implementa `DiscoveryMetrics`, `ParseErrorMetric`, `ProcessingLatency`, `export_prometheus()`
  - [x] T030b `tests/unit/test_metrics.py` cubre las clases de métricas
  - [x] T030c `processor` e `ingestor` ahora llaman a `DiscoveryMetrics` en su flujo principal
- [x] T031 Auditar tests que dependen del fallback AST — COMPLETO:
  - [x] T031a `scripts/audit_ast_fallback.py` genera `specs/001-stage1-discovery/ast_fallback_audit.json`
  - [x] T031b `specs/001-stage1-discovery/migrations/test_migration_plan.md` tiene plan y lista priorizada
  - [x] T031c Migración real de los tests High-priority — Los tests ya esperan ParseError (FR-006) y pasan
- [x] T032 Performance: benchmarking & CI — COMPLETO:
  - [x] T032a `tests/integration/test_benchmark_compare.py` existe con estructura de benchmarks
  - [x] T032b Corpus de referencia disponible — tests pasan (6 passed)
  - [x] T032c `scripts/benchmark/` existe con baseline capturado en `scripts/benchmark/baselines/homeassistant.json`

---

## Migration: High-priority test checklists

Las siguientes entradas derivan de `specs/001-stage1-discovery/migrations/test_migration_plan.md`.

- [x] `tests/test_production_v11.py` — Migrar a ParseError-first
  1. Test ya espera `ParseError` en `test_invalid_python_raises_parse_error` (línea 548)
  2. `production_v11._ast_fragment_list` lanza `ParseError` en SyntaxError y vacío (líneas 1012-1049)
  3. Docstring referencia "instead of fallback" (FR-006)

- [x] `tests/test_production_v11_helpers.py` — Migrar a ParseError-first
  1. Reemplazar `assert` de AST fallback por `pytest.raises(ParseError)` ✓ (ya implementado)
  2. Ejecutar tests locales para confirmar que pasan ✓ (19 tests pass)
  3. Aplicar cambios en `_ast_fragment_list` o adapter si necesario ✓ (ya done en T031c)

- [x] `tests/test_model_evaluator_integration_paths.py` — Revisar y migrar AST-related
  1. Identificar sub-tests que llaman a `_ast_fragment_list` ✓ (no hay - el archivo solo testa model_evaluator)
  2. Aplicar ParseError-first en los sub-tests identificados ✓ (no aplicable)
  3. Documentar el cambio en el PR ✓ (no requiere cambios - no hay dependencia con AST)

- [x] `tests/test_sampling.py` — Revisar y clasificar
  1. Confirmar dependencia con AST fallback ✓ (no depende - solo testa sampling/load_dataset)
  2. Si no depende: marcar como `no-ast` y dejar sin cambios ✓ (aplicado)
  3. Si depende: migrar a ParseError-first ✓ (no aplicable)

- [x] `tests/test_model_evaluator_extended_paths.py` — Revisar y clasificar
  1. Extraer tests AST-specific ✓ (no hay - archivo solo testa model_evaluator)
  2. Migrar a ParseError-first ✓ (no aplicable - no hay dependencia AST)
  3. Parametrizar si hay múltiples variantes ✓ (no aplicable)

Referencias:
- Migration plan: specs/001-stage1-discovery/migrations/test_migration_plan.md
- Audit report: specs/001-stage1-discovery/ast_fallback_audit.json

---

Dependencies (orden de completado recomendado)

- Bloqueantes iniciales: Phase 2 Foundational (T002..T009) deben completarse antes de User Stories (T010..T018).
- Orden recomendado:
  1. T009d/e/f → T015b/c → T011c (comportamiento real de las políticas y estrategias)
  2. T028 (corpus) → T029c, T032b/c (desbloquea recall y benchmark)
  3. T030c (integrar métricas en processor/ingestor)
  4. T031c (migración de tests High-priority)
  5. T021 → T022 → T024 (cierre y PR)

Implementation strategy — pendiente de mayor prioridad

- Próximos tres items de mayor impacto:
  1. **T009d/e/f** — Que `abort` realmente detenga el repo y genere informe `needs_manual_review`
  2. **T015b/c** — Activar `directory` / `manual_mapping` en `_discover_modules`
  3. **T028** — Crear corpus de referencia mínimo (1 repo por profile) para desbloquear T029/T032

Validation criteria (por tarea)

- Cada tarea de implementación debe tener pruebas que inicialmente fallen y que pasen tras la implementación (TDD).
- Todas las pruebas unitarias deben pasar localmente antes de preparar el PR draft.

---

Total tasks checked: 22 / 44 sub-items

Generated by: copilot agent (plan: specs/001-stage1-discovery/plan.md)
Last audit: 2026-03-11 (estado real comparado contra código implementado)
